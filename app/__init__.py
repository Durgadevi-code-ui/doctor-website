"""
app/__init__.py
----------------
The application factory. `create_app()` builds a fully configured
Flask app: it loads config, binds the database/migration/rate-limiter
extensions, registers the customers + admin blueprints, sets up
logging, CSRF protection, secure response headers, and installs
top-level JSON error handlers.

Using a factory (rather than a single module-level `Flask(__name__)`)
is standard practice because it lets the same codebase be instantiated
multiple times with different configs - one real instance for the
running server, and a separate throwaway instance per test in
tests/conftest.py.
"""

import os

from flask import Flask, jsonify, render_template
from flask_wtf.csrf import CSRFProtect

from app.config import config_map
from app.database import db, migrate, limiter
from app.utils.logging_config import configure_logging

csrf = CSRFProtect()


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_map.get(config_name, config_map["default"]))

    configure_logging(app)

    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    csrf.init_app(app)

    # Import models so Flask-Migrate/Alembic can detect them for
    # autogenerate. This import must happen after db.init_app().
    from app.models import customer  # noqa: F401
    from app.models import admin_user  # noqa: F401

    from app.routes.customer_routes import customers_bp
    app.register_blueprint(customers_bp)

    from app.routes.admin_routes import admin_bp
    app.register_blueprint(admin_bp)

    # The public intake API is a stateless, cookie-less JSON endpoint -
    # CSRF tokens protect cookie/session-authenticated form submissions,
    # which this isn't, so it's exempted here rather than forced to
    # carry a token it has no session to tie to.
    csrf.exempt(customers_bp)
    # The admin blueprint mixes traditional HTML forms (login, OTP,
    # logout - which validate their own CSRF token explicitly inside
    # app/routes/admin_routes.py) with JSON fetch()-based dashboard
    # actions (which authenticate via the admin session cookie
    # instead). Exempted here at the blueprint level so the JSON
    # routes don't get a false "CSRF token missing" error; the three
    # form routes call flask_wtf.csrf.validate_csrf() themselves.
    csrf.exempt(admin_bp)

    _register_cli_commands(app)

    @app.get("/")
    def index():
        """Serve the public customer intake form. No customer data is
        ever rendered here - see app/routes/admin_routes.py for the
        only place records are readable."""
        return render_template("index.html")

    @app.get("/health")
    def health():
        """Lightweight liveness endpoint for uptime checks / Docker healthcheck."""
        return jsonify({"status": "ok"}), 200

    @app.after_request
    def set_secure_headers(response):
        """Baseline secure headers on every response. Content-Security-Policy
        allows the specific CDNs this app loads Three.js/GSAP/fonts from -
        tighten further if you remove any of those CDN dependencies."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if not app.debug:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )
        return response

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"success": False, "message": "Resource not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return jsonify({"success": False, "message": "Method not allowed."}), 405

    @app.errorhandler(429)
    def rate_limited(_error):
        return jsonify({"success": False, "message": "Too many requests. Please try again shortly."}), 429

    @app.errorhandler(500)
    def server_error(_error):
        app.logger.exception("Unhandled server error")
        return jsonify({"success": False, "message": "Internal server error."}), 500

    return app


def _register_cli_commands(app):
    """
    `flask create-admin` - interactive bootstrap for the first (or an
    additional) admin account. Not exposed as a web route on purpose:
    admin account creation should be a controlled, operator-run action,
    not a public or even an authenticated-admin HTTP endpoint.
    """
    @app.cli.command("create-admin")
    def create_admin():
        import getpass

        from app.database import db
        from app.models.admin_user import AdminUser

        username = input("Admin username: ").strip()
        email = input("Admin email (for OTP delivery): ").strip()
        password = getpass.getpass("Admin password: ")

        if AdminUser.query.filter_by(username=username).first():
            print(f"An admin with username '{username}' already exists.")
            return

        admin = AdminUser(username=username, email=email)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"Admin '{username}' created.")
