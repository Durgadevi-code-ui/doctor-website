"""
app/services/customer_service.py
----------------------------------
Business logic for the Customer resource, kept separate from
app/routes/customer_routes.py so that:
  - routes stay thin (parse request -> call service -> format response)
  - the same logic is reusable/testable without spinning up Flask's
    request context (see tests/test_customers_api.py)

Two small custom exceptions (`DuplicateCustomerError`,
`CustomerNotFoundError`) let routes translate service-layer outcomes
into the right HTTP status code without the service layer needing to
know anything about Flask or HTTP.
"""

import csv
import io

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.database import db
from app.models.customer import Customer


class DuplicateCustomerError(Exception):
    """Raised when a create/update would violate the phone/email uniqueness rules."""


class CustomerNotFoundError(Exception):
    """Raised when a lookup by customer_id finds no matching row."""


def _find_duplicate(phone_number, email, exclude_id=None):
    """
    Duplicate rule for the Washington DC Doctors Meet intake revision:
    a match on EITHER phone number OR email address (against any other
    customer) is a duplicate. Per-field messages ("Phone number
    already exists." / "Email already exists.") were simplified into
    a single message on purpose - see CHANGELOG.md, "Duplicate
    validation" - matching customer names is intentionally never
    checked.

    Returns "This email or contact number is already registered." if either field matches an
    existing row, otherwise None (safe to insert/update).
    """
    query = Customer.query.filter(
        or_(Customer.phone_number == phone_number, Customer.email == email)
    )
    if exclude_id is not None:
        query = query.filter(Customer.customer_id != exclude_id)

    if query.first():
        return "This email or contact number is already registered."
    return None


def create_customer(cleaned):
    """
    Create a new customer from an already-validated `cleaned` dict
    (see app/utils/validators.py). Raises DuplicateCustomerError if
    the phone number or email is already on file.
    """
    conflict = _find_duplicate(cleaned["phone_number"], cleaned["email"])
    if conflict:
        raise DuplicateCustomerError(conflict)

    customer = Customer(**cleaned)
    db.session.add(customer)
    try:
        db.session.commit()
    except IntegrityError:
        # Safety net for a race condition between the check above and
        # this commit - the UNIQUE constraints are the final authority.
        db.session.rollback()
        raise DuplicateCustomerError("This email or contact number is already registered.")

    return customer


def update_customer(customer_id, cleaned):
    """Update an existing customer. Raises CustomerNotFoundError /
    DuplicateCustomerError as appropriate."""
    customer = Customer.query.get(customer_id)
    if not customer:
        raise CustomerNotFoundError(f"Customer {customer_id} not found.")

    conflict = _find_duplicate(
        cleaned["phone_number"], cleaned["email"], exclude_id=customer_id
    )
    if conflict:
        raise DuplicateCustomerError(conflict)

    for field, value in cleaned.items():
        setattr(customer, field, value)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise DuplicateCustomerError("This email or contact number is already registered.")

    return customer


def get_customer(customer_id):
    customer = Customer.query.get(customer_id)
    if not customer:
        raise CustomerNotFoundError(f"Customer {customer_id} not found.")
    return customer


def list_customers(
    page=1,
    per_page=20,
    search=None,
    specialty=None,
    interested_service=None,
    include_inactive=False,
):
    """
    Bonus features: search, filter by specialty/service interest, and
    pagination, all in one query. Returns (items, total_count).
    """
    query = Customer.query

    if not include_inactive:
        query = query.filter(Customer.is_active.is_(True))

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Customer.customer_name.ilike(like),
                Customer.business_name.ilike(like),
                Customer.email.ilike(like),
                Customer.phone_number.ilike(like),
            )
        )

    if specialty:
        query = query.filter(Customer.specialty.ilike(specialty))

    if interested_service:
        # interested_service now stores a comma-joined multi-select
        # value (e.g. "AI Receptionist, AI Chatbot"), so an exact
        # match would miss customers who also picked other services.
        # A "contains" match keeps the filter working correctly.
        query = query.filter(Customer.interested_service.ilike(f"%{interested_service}%"))

    query = query.order_by(Customer.created_at.desc())

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return items, total


def delete_customer(customer_id, hard=False):
    """
    Bonus feature: soft delete by default (flips is_active to False,
    preserving history), with an optional hard-delete path for
    permanent removal.
    """
    customer = Customer.query.get(customer_id)
    if not customer:
        raise CustomerNotFoundError(f"Customer {customer_id} not found.")

    if hard:
        db.session.delete(customer)
    else:
        customer.is_active = False

    db.session.commit()
    return customer


def get_statistics():
    """Admin dashboard aggregate counts: total, today's registrations,
    and breakdowns by specialty / interested service."""
    from datetime import datetime, timedelta

    total = Customer.query.filter(Customer.is_active.is_(True)).count()

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = Customer.query.filter(
        Customer.is_active.is_(True),
        Customer.created_at >= today_start,
        Customer.created_at < today_start + timedelta(days=1),
    ).count()

    by_specialty = (
        db.session.query(Customer.specialty, db.func.count(Customer.customer_id))
        .filter(Customer.is_active.is_(True))
        .group_by(Customer.specialty)
        .all()
    )
    by_service = (
        db.session.query(Customer.interested_service, db.func.count(Customer.customer_id))
        .filter(Customer.is_active.is_(True))
        .group_by(Customer.interested_service)
        .all()
    )

    return {
        "total_customers": total,
        "today_registrations": today_count,
        "by_specialty": {row[0] or "Unspecified": row[1] for row in by_specialty},
        "by_interested_service": {row[0] or "Unspecified": row[1] for row in by_service},
    }


def export_customers_csv(include_inactive=False):
    """Bonus feature: export all customers to a CSV string."""
    query = Customer.query
    if not include_inactive:
        query = query.filter(Customer.is_active.is_(True))
    customers = query.order_by(Customer.created_at.desc()).all()

    output = io.StringIO()
    fieldnames = [
        "customer_id", "customer_name", "customer_role", "phone_number", "email",
        "business_name", "practice_type", "practice_type_other", "specialty", "locations",
        "pain_point", "daily_calls", "interested_service", "additional_notes",
        "is_active", "created_at", "updated_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for customer in customers:
        writer.writerow(customer.to_dict())

    return output.getvalue()
