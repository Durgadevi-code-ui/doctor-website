"""
app/routes/customer_routes.py
--------------------------------
Public-facing intake API, mounted under /api/customers.

SECURITY NOTE (Washington DC Doctors Meet privacy requirement): this
blueprint now exposes ONLY the create (POST) endpoint. The previous
GET (list/single), PUT, DELETE, /stats, and /export endpoints were
REMOVED from here - not made stricter, removed - because customer
data must never be publicly readable after submission. The exact same
underlying service functions (app/services/customer_service.py were
NOT duplicated) are now called from the new, authenticated
app/routes/admin_routes.py blueprint instead, mounted under
/admin/api/customers/*. See CHANGELOG.md, "Public dashboard removed".

Endpoints
  POST /api/customers   create a customer (duplicate-checked, public)
"""

from flask import Blueprint, current_app, request

from app.database import limiter
from app.services import customer_service as service
from app.utils.responses import error_response, success_response, validation_error_response
from app.utils.validators import validate_customer_payload

customers_bp = Blueprint("customers", __name__, url_prefix="/api/customers")


@customers_bp.post("")
@limiter.limit("30 per hour")
def create_customer():
    payload = request.get_json(silent=True) or {}
    errors, cleaned = validate_customer_payload(payload)
    if errors:
        return validation_error_response(errors)

    try:
        customer = service.create_customer(cleaned)
    except service.DuplicateCustomerError as exc:
        return error_response(str(exc), status_code=409)

    current_app.logger.info("Created customer %s", customer.customer_id)
    return success_response(
        "Customer created successfully.",
        status_code=201,
        customer_id=customer.customer_id,
        data=customer.to_dict(),
    )
