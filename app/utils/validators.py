"""
app/utils/validators.py
------------------------
Server-side validation for every field on the customer/practice intake
form. The frontend (static/js/script.js) also validates for a
responsive UX, but that check is a convenience only - it can be
bypassed by anyone calling the API directly, so every rule here runs
unconditionally on the backend before anything reaches the database.

`validate_customer_payload()` returns a (errors, cleaned) tuple:
  - errors:  dict of field_name -> message, matching the
             `{"success": false, "errors": {...}}` response shape
             requested for validation failures.
  - cleaned: dict of trimmed/normalized values, populated only for
             fields that passed validation.
"""

import re

# Stricter than a simple "has an @ and a dot" check: rejects a local
# part or domain that starts/ends with a dot, and rejects consecutive
# dots, in addition to requiring a real domain with a TLD.
#
# Verified against the exact cases from the Washington DC Doctors Meet
# intake spec:
#   valid:   doctor@example.com                          -> True
#   invalid: abc@ / test.com / user@.com / a@b..com       -> False
EMAIL_RE = re.compile(
    r"^(?!\.)[A-Za-z0-9._%+\-]+(?<!\.)@"
    r"(?!\.)[A-Za-z0-9.\-]+(?<!\.)\.[A-Za-z]{2,}$"
)
PHONE_ALLOWED_RE = re.compile(r"^[\d\s\-\+\(\)]+$")
PHONE_DIGITS_RE = re.compile(r"\d")

MIN_PHONE_DIGITS = 7

FIELD_LIMITS = {
    "customer_name": 150,
    "customer_role": 100,
    "phone_number": 20,
    "email": 255,
    "business_name": 200,
    "practice_type": 100,
    "practice_type_other": 150,
    "specialty": 100,
    "pain_point": 5000,
    # Widened to 255: interested_service now stores a comma-joined
    # list from the multi-select checkbox UI, not one chip value.
    "interested_service": 255,
    "additional_notes": 5000,
}

# Friendlier, field-specific wording for the most visible required
# fields (Washington DC Doctors Meet intake revision). Any required
# field not listed here still falls back to the generic
# "<Field name> is required." message below.
REQUIRED_MESSAGES = {
    "customer_name": "Please enter your full name.",
    "phone_number": "A valid phone number is required.",
    "email": "A valid email address is required.",
    "business_name": "Practice / business name is required.",
    "practice_type": "Please select your practice type.",
    "specialty": "Please select your specialty.",
    "pain_point": "Please select your biggest front-desk pain point.",
    "interested_service": "Please select at least one service you're interested in.",
}

REQUIRED_FIELDS = [
    "customer_name",
    "phone_number",
    "email",
    "business_name",
    "practice_type",
    "specialty",
    "pain_point",
    "interested_service",
]

OPTIONAL_TEXT_FIELDS = ["customer_role", "additional_notes"]
# NOTE: practice_type_other is NOT in this list - it's handled by its
# own conditional block below, since it's required only when
# practice_type == "Other" (not simply optional).
OPTIONAL_INT_FIELDS = ["locations", "daily_calls"]


def _clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def validate_customer_payload(data):
    errors = {}
    cleaned = {}

    if not isinstance(data, dict):
        return {"_general": "Request body must be a JSON object."}, {}

    # --- Required text fields ---
    for field in REQUIRED_FIELDS:
        value = _clean_text(data.get(field))
        limit = FIELD_LIMITS.get(field)
        if not value:
            errors[field] = REQUIRED_MESSAGES.get(
                field, f"{field.replace('_', ' ').capitalize()} is required."
            )
            continue
        if limit and len(value) > limit:
            errors[field] = f"{field.replace('_', ' ').capitalize()} must be {limit} characters or fewer."
            continue
        cleaned[field] = value

    # --- Conditional: "Please specify your practice" textbox ---
    # Only required when practice_type == "Other"; otherwise cleared
    # so a stray value can't linger against a different practice_type.
    if cleaned.get("practice_type") == "Other":
        other_value = _clean_text(data.get("practice_type_other"))
        limit = FIELD_LIMITS.get("practice_type_other")
        if not other_value:
            errors["practice_type_other"] = "Please specify your practice."
        elif limit and len(other_value) > limit:
            errors["practice_type_other"] = f"Practice type must be {limit} characters or fewer."
        else:
            cleaned["practice_type_other"] = other_value
    else:
        cleaned["practice_type_other"] = None

    # --- Optional text fields ---
    for field in OPTIONAL_TEXT_FIELDS:
        value = _clean_text(data.get(field))
        limit = FIELD_LIMITS.get(field)
        if value and limit and len(value) > limit:
            errors[field] = f"{field.replace('_', ' ').capitalize()} must be {limit} characters or fewer."
        else:
            cleaned[field] = value or None

    # --- Email format (overrides the generic required-field check above) ---
    if "email" in cleaned:
        email = cleaned["email"].lower()
        if not EMAIL_RE.match(email):
            errors["email"] = "Enter a valid email address."
            cleaned.pop("email", None)
        else:
            cleaned["email"] = email

    # --- Phone format ---
    if "phone_number" in cleaned:
        phone = cleaned["phone_number"]
        if not PHONE_ALLOWED_RE.match(phone):
            errors["phone_number"] = "Phone number may only contain digits, spaces, and + - ( ) characters."
            cleaned.pop("phone_number", None)
        elif len(PHONE_DIGITS_RE.findall(phone)) < MIN_PHONE_DIGITS:
            errors["phone_number"] = f"Phone number must contain at least {MIN_PHONE_DIGITS} digits."
            cleaned.pop("phone_number", None)

    # --- Optional integer fields ---
    for field in OPTIONAL_INT_FIELDS:
        raw = data.get(field)
        if raw in (None, ""):
            cleaned[field] = None
            continue
        try:
            int_value = int(raw)
            if int_value < 0:
                raise ValueError
            cleaned[field] = int_value
        except (TypeError, ValueError):
            errors[field] = f"{field.replace('_', ' ').capitalize()} must be a whole number of 0 or more."

    return errors, cleaned
