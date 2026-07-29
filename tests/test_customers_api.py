"""
tests/test_customers_api.py
------------------------------
Integration tests for the PUBLIC /api/customers endpoint.

As of the Washington DC Doctors Meet privacy revision, this is the
ONLY public customer-facing route - it accepts submissions but never
returns customer data. Reading, updating, deleting, and exporting
customer records now requires an authenticated admin session; see
tests/test_admin_routes.py for those.

Run with:
    pytest -v
"""


def test_create_customer_success(client, sample_payload):
    res = client.post("/api/customers", json=sample_payload)
    body = res.get_json()

    assert res.status_code == 201
    assert body["success"] is True
    assert body["message"] == "Customer created successfully."
    assert isinstance(body["customer_id"], int)


def test_missing_required_fields_returns_400(client):
    res = client.post("/api/customers", json={})
    body = res.get_json()

    assert res.status_code == 400
    assert body["success"] is False
    assert "customer_name" in body["errors"]
    assert "email" in body["errors"]
    assert "phone_number" in body["errors"]
    assert "practice_type" in body["errors"]


def test_invalid_email_returns_400(client, sample_payload):
    for bad_email in ["not-an-email", "abc@", "test.com", "user@.com"]:
        sample_payload["email"] = bad_email
        res = client.post("/api/customers", json=sample_payload)
        body = res.get_json()
        assert res.status_code == 400, f"expected 400 for {bad_email!r}"
        assert "email" in body["errors"]


def test_practice_type_other_requires_specify_text(client, sample_payload):
    sample_payload["practice_type"] = "Other"
    res = client.post("/api/customers", json=sample_payload)
    body = res.get_json()

    assert res.status_code == 400
    assert "practice_type_other" in body["errors"]

    sample_payload["practice_type_other"] = "Wellness Clinic"
    res = client.post("/api/customers", json=sample_payload)
    assert res.status_code == 201


def test_duplicate_phone_different_email(client, sample_payload):
    """Washington DC Doctors Meet revision: ANY match on phone OR email
    (against a different customer) is reported as the single, unified
    'This email or contact number is already registered.' message -
    see CHANGELOG.md, 'Duplicate validation'."""
    client.post("/api/customers", json=sample_payload)

    second = dict(sample_payload)
    second["email"] = "different@example.com"
    res = client.post("/api/customers", json=second)
    body = res.get_json()

    assert res.status_code == 409
    assert body["message"] == "This email or contact number is already registered."


def test_duplicate_email_different_phone(client, sample_payload):
    client.post("/api/customers", json=sample_payload)

    second = dict(sample_payload)
    second["phone_number"] = "5559998888"
    res = client.post("/api/customers", json=second)
    body = res.get_json()

    assert res.status_code == 409
    assert body["message"] == "This email or contact number is already registered."


def test_duplicate_phone_and_email(client, sample_payload):
    client.post("/api/customers", json=sample_payload)

    res = client.post("/api/customers", json=sample_payload)
    body = res.get_json()

    assert res.status_code == 409
    assert body["message"] == "This email or contact number is already registered."


def test_public_read_update_delete_endpoints_removed(client, sample_payload):
    """Regression guard for the privacy requirement: customer records
    must never be publicly readable. These routes existed before this
    revision and must now return 404/405, not customer data."""
    create_res = client.post("/api/customers", json=sample_payload)
    customer_id = create_res.get_json()["customer_id"]

    assert client.get("/api/customers").status_code in (404, 405)
    assert client.get(f"/api/customers/{customer_id}").status_code in (404, 405)
    assert client.put(f"/api/customers/{customer_id}", json={}).status_code in (404, 405)
    assert client.delete(f"/api/customers/{customer_id}").status_code in (404, 405)
    assert client.get("/api/customers/stats").status_code in (404, 405)
    assert client.get("/api/customers/export").status_code in (404, 405)
