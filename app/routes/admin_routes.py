"""
app/routes/admin_routes.py
-----------------------------
Admin authentication (username+password, then email OTP) and the
protected Admin Dashboard - the ONLY place customer records can be
viewed, searched, filtered, edited, deleted, or exported after the
Washington DC Doctors Meet privacy revision (see CHANGELOG.md).

Reuses the exact same app/services/customer_service.py functions the
old public dashboard used - no business logic was duplicated, only
moved behind authentication.

Routes
  GET/POST /admin/login          step 1: username + password
  GET/POST /admin/verify-otp     step 2: email OTP
  POST     /admin/logout
  GET      /admin/dashboard      HTML page (protected)
  GET      /admin/api/customers            list (search/filter/paginate)
  GET      /admin/api/customers/<id>        fetch one
  PUT      /admin/api/customers/<id>        update
  DELETE   /admin/api/customers/<id>        delete
  GET      /admin/api/customers/export      CSV export
  GET      /admin/api/stats                 dashboard aggregate counts
"""

from flask import Blueprint, Response, render_template, request, session
from flask_wtf.csrf import ValidationError, validate_csrf

from app.database import limiter
from app.models.admin_user import AdminUser
from app.services import customer_service as service
from app.utils.responses import error_response, success_response, validation_error_response
from app.utils.security import admin_login_required, log_audit, send_otp_email
from app.utils.validators import validate_customer_payload

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _check_csrf():
    """Manually validates the CSRF token for the admin blueprint's three
    traditional form posts (login, verify-otp, logout), since the
    blueprint itself is exempted from Flask-WTF's automatic check to
    let its JSON dashboard routes work - see app/__init__.py."""
    try:
        validate_csrf(request.form.get("csrf_token", ""))
        return None
    except ValidationError:
        return render_template("admin_login.html", error="Your session expired. Please try again."), 400


# ---------------------------------------------------------------- #
# Authentication: step 1 (password) and step 2 (email OTP)
# ---------------------------------------------------------------- #

@admin_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if request.method == "GET":
        return render_template("admin_login.html", error=None)

    csrf_error = _check_csrf()
    if csrf_error:
        return csrf_error

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    admin = AdminUser.query.filter_by(username=username, is_active=True).first()

    # Constant-shape response whether the username exists or not, to
    # avoid leaking which admin usernames are valid.
    if not admin or not admin.check_password(password):
        log_audit("admin_login_failed", actor=username or "unknown")
        return render_template("admin_login.html", error="Invalid username or password."), 401

    code = admin.issue_otp()
    from app.database import db
    db.session.commit()
    send_otp_email(admin.email, code)

    session["pending_admin_id"] = admin.id
    log_audit("admin_password_ok_otp_sent", actor=admin.username)
    return render_template("admin_otp.html", error=None)


@admin_bp.route("/verify-otp", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def verify_otp():
    pending_id = session.get("pending_admin_id")
    if not pending_id:
        return render_template("admin_login.html", error="Please log in again."), 401

    if request.method == "GET":
        return render_template("admin_otp.html", error=None)

    csrf_error = _check_csrf()
    if csrf_error:
        return csrf_error

    from app.database import db
    admin = AdminUser.query.get(pending_id)
    submitted_code = (request.form.get("otp_code") or "").strip()

    if not admin or not admin.verify_otp(submitted_code):
        db.session.commit()  # persist the incremented attempt counter even on failure
        log_audit("admin_otp_failed", actor=getattr(admin, "username", "unknown"))
        return render_template("admin_otp.html", error="Incorrect or expired code."), 401

    from datetime import datetime
    admin.last_login_at = datetime.utcnow()
    db.session.commit()

    session.pop("pending_admin_id", None)
    session["admin_id"] = admin.id
    session["admin_username"] = admin.username
    log_audit("admin_login_success", actor=admin.username)
    return render_template("admin_dashboard.html", admin_username=admin.username)


@admin_bp.post("/logout")
def logout():
    actor = session.get("admin_username", "unknown")
    session.pop("admin_id", None)
    session.pop("admin_username", None)
    session.pop("pending_admin_id", None)
    log_audit("admin_logout", actor=actor)
    return render_template("admin_login.html", error=None)


# ---------------------------------------------------------------- #
# Protected dashboard page
# ---------------------------------------------------------------- #

@admin_bp.get("/dashboard")
@admin_login_required
def dashboard():
    return render_template("admin_dashboard.html", admin_username=session.get("admin_username"))


# ---------------------------------------------------------------- #
# Protected JSON API - the ONLY place customer records are readable
# ---------------------------------------------------------------- #

@admin_bp.get("/api/customers")
@admin_login_required
def list_customers():
    try:
        page = max(int(request.args.get("page", 1)), 1)
    except ValueError:
        page = 1
    try:
        per_page = int(request.args.get("per_page", 20))
    except ValueError:
        per_page = 20
    per_page = max(1, min(per_page, 100))

    search = request.args.get("search", "").strip() or None
    specialty = request.args.get("specialty", "").strip() or None
    interested_service = request.args.get("interested_service", "").strip() or None
    include_inactive = request.args.get("include_inactive", "false").lower() == "true"

    items, total = service.list_customers(
        page=page, per_page=per_page, search=search, specialty=specialty,
        interested_service=interested_service, include_inactive=include_inactive,
    )
    return success_response(
        "Customers retrieved successfully.",
        data={
            "customers": [c.to_dict() for c in items],
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page if per_page else 0,
        },
    )


@admin_bp.get("/api/stats")
@admin_login_required
def stats():
    return success_response("Statistics retrieved successfully.", data=service.get_statistics())


@admin_bp.get("/api/customers/export")
@admin_login_required
def export_customers():
    include_inactive = request.args.get("include_inactive", "false").lower() == "true"
    csv_data = service.export_customers_csv(include_inactive=include_inactive)
    log_audit("admin_export_csv", actor=session.get("admin_username"))
    return Response(
        csv_data, mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=customers.csv"},
    )


@admin_bp.get("/api/customers/<int:customer_id>")
@admin_login_required
def get_customer(customer_id):
    try:
        customer = service.get_customer(customer_id)
    except service.CustomerNotFoundError as exc:
        return error_response(str(exc), status_code=404)
    return success_response("Customer retrieved successfully.", data=customer.to_dict())


@admin_bp.put("/api/customers/<int:customer_id>")
@admin_login_required
def update_customer(customer_id):
    payload = request.get_json(silent=True) or {}
    errors, cleaned = validate_customer_payload(payload)
    if errors:
        return validation_error_response(errors)

    try:
        customer = service.update_customer(customer_id, cleaned)
    except service.CustomerNotFoundError as exc:
        return error_response(str(exc), status_code=404)
    except service.DuplicateCustomerError as exc:
        return error_response(str(exc), status_code=409)

    log_audit("admin_customer_update", actor=session.get("admin_username"), details=f"customer_id={customer_id}")
    return success_response(
        "Customer updated successfully.",
        customer_id=customer.customer_id,
        data=customer.to_dict(),
    )


@admin_bp.delete("/api/customers/<int:customer_id>")
@admin_login_required
def delete_customer(customer_id):
    hard = request.args.get("hard", "false").lower() == "true"
    try:
        service.delete_customer(customer_id, hard=hard)
    except service.CustomerNotFoundError as exc:
        return error_response(str(exc), status_code=404)

    log_audit(
        "admin_customer_delete", actor=session.get("admin_username"),
        details=f"customer_id={customer_id} hard={hard}",
    )
    message = "Customer permanently deleted." if hard else "Customer deleted."
    return success_response(message)
