"""
app/utils/security.py
-----------------------
Security helpers shared by the admin auth system:

  - send_otp_email()      - delivers the 2FA code
  - log_audit()            - structured audit-trail logging
  - admin_login_required   - route decorator protecting admin pages/API

Rate limiting itself lives in app/__init__.py (Flask-Limiter is
initialized there, once, and applied per-route as a decorator) rather
than here, since it needs the shared `limiter` instance available at
import time in routes.
"""

import smtplib
from email.mime.text import MIMEText
from functools import wraps

from flask import current_app, jsonify, redirect, request, session, url_for


def send_otp_email(to_email, code):
    """
    Sends the 2FA code by email. If SMTP isn't configured (no
    SMTP_HOST in the environment - the common case for local dev and
    for this sandboxed handoff, which has no mail server available),
    the code is written to the application log instead of silently
    failing, so the admin login flow is still fully testable without
    a real mailbox. Configure SMTP_* in .env for production use - see
    README "Admin 2FA Setup".
    """
    smtp_host = current_app.config.get("SMTP_HOST")

    if not smtp_host:
        current_app.logger.warning(
            "SMTP_HOST not configured - logging OTP instead of emailing it. "
            "Admin OTP for %s: %s (valid %s minutes)",
            to_email, code, current_app.config.get("OTP_VALIDITY_MINUTES", 10),
        )
        return True

    try:
        message = MIMEText(
            f"Your Agentic Atoms admin verification code is: {code}\n"
            f"This code expires in {current_app.config.get('OTP_VALIDITY_MINUTES', 10)} minutes."
        )
        message["Subject"] = "Your Agentic Atoms admin verification code"
        message["From"] = current_app.config.get("OTP_FROM_EMAIL", "no-reply@agenticatoms.com")
        message["To"] = to_email

        with smtplib.SMTP(smtp_host, current_app.config.get("SMTP_PORT", 587), timeout=10) as server:
            server.starttls()
            smtp_user = current_app.config.get("SMTP_USER")
            smtp_password = current_app.config.get("SMTP_PASSWORD")
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.send_message(message)
        return True
    except (smtplib.SMTPException, OSError):
        current_app.logger.exception("Failed to send OTP email to %s", to_email)
        return False


def log_audit(action, actor="anonymous", details=""):
    """
    Writes a single structured audit-log line. Kept intentionally
    simple (no new table) - every admin-affecting action (login
    success/failure, OTP verify, customer edit/delete) is written
    here, and shows up in the same rotating logs/app.log configured
    in app/utils/logging_config.py, tagged AUDIT so it's easy to grep
    or ship to a log aggregator later.
    """
    current_app.logger.info("AUDIT action=%s actor=%s details=%s", action, actor, details)


def _is_api_request():
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.path.startswith("/admin/api/")
    )


def admin_login_required(view_func):
    """
    Protects an admin route. Requires a fully authenticated admin
    session (session["admin_id"] set only after BOTH factors -
    password AND OTP - succeed; see app/routes/admin_routes.py).

    Returns a 401 JSON response for AJAX/API calls (detected via the
    X-Requested-With header the admin dashboard's fetch() calls send,
    or the /admin/api/ path prefix), or a redirect to the login page
    for ordinary browser navigation.
    """
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            if _is_api_request():
                return jsonify({"success": False, "message": "Authentication required."}), 401
            return redirect(url_for("admin.login"))
        return view_func(*args, **kwargs)
    return wrapped
