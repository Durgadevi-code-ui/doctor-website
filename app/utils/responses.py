"""
app/utils/responses.py
------------------------
Small helpers that build the standardized JSON response envelope
requested for this API:

  success:    {"success": true,  "message": "...", "customer_id": 101, "data": {...}}
  duplicate:  {"success": false, "message": "Customer already exists."}
  validation: {"success": false, "errors": {"email": "Invalid email format"}}

Centralizing this in one place keeps every route returning the exact
same shape, rather than each endpoint hand-rolling its own dict.
"""

from flask import jsonify


def success_response(message, status_code=200, data=None, customer_id=None):
    body = {"success": True, "message": message}
    if customer_id is not None:
        body["customer_id"] = customer_id
    if data is not None:
        body["data"] = data
    return jsonify(body), status_code


def error_response(message, status_code=400):
    return jsonify({"success": False, "message": message}), status_code


def validation_error_response(errors, status_code=400):
    return jsonify({"success": False, "errors": errors}), status_code
