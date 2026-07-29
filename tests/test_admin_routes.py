"""
tests/test_admin_routes.py
-----------------------------
Integration tests for the admin authentication (password + email OTP)
flow and the protected /admin/api/* endpoints that now host all
customer read/update/delete/export functionality.

The real send_otp_email() would try to reach an SMTP server (or just
log the code, if SMTP_HOST is unset - see app/utils/security.py).
Either way, the test can't read the code back out of a real inbox or
the log, so these tests monkeypatch app.routes.admin_routes.send_otp_email
to capture the code directly - this tests the same OTP
generation/hashing/verification logic (app/models/admin_user.py) that
runs in production, just swaps out the delivery mechanism, exactly
the way you'd unit test any code that sends an external notification.

Run with:
    pytest -v
"""

from tests.conftest import extract_csrf_token


def _login_step_one(client, monkeypatch, username="testadmin", password="Testpass123!"):
    """Submits the password step and returns the OTP code that would
    have been emailed, captured via the monkeypatched send function."""
    captured = {}

    def fake_send_otp_email(to_email, code):
        captured["code"] = code
        return True

    monkeypatch.setattr("app.routes.admin_routes.send_otp_email", fake_send_otp_email)

    login_page = client.get("/admin/login")
    token = extract_csrf_token(login_page.get_data(as_text=True))

    res = client.post(
        "/admin/login",
        data={"username": username, "password": password, "csrf_token": token},
    )
    return res, captured.get("code")


def _full_login(client, monkeypatch):
    """Completes both factors and returns the final response."""
    _, code = _login_step_one(client, monkeypatch)
    otp_page = client.get("/admin/verify-otp")
    token = extract_csrf_token(otp_page.get_data(as_text=True))
    return client.post("/admin/verify-otp", data={"otp_code": code, "csrf_token": token})


def test_login_page_loads(client):
    res = client.get("/admin/login")
    assert res.status_code == 200
    assert b"Admin Login" in res.data


def test_login_invalid_credentials_rejected(client, admin_user):
    login_page = client.get("/admin/login")
    token = extract_csrf_token(login_page.get_data(as_text=True))

    res = client.post(
        "/admin/login",
        data={"username": "testadmin", "password": "wrong-password", "csrf_token": token},
    )
    assert res.status_code == 401
    assert b"Invalid username or password" in res.data


def test_full_login_otp_flow_succeeds(client, admin_user, monkeypatch):
    step_one_res, code = _login_step_one(client, monkeypatch)
    assert step_one_res.status_code == 200
    assert code is not None and len(code) == 6

    otp_page = client.get("/admin/verify-otp")
    token = extract_csrf_token(otp_page.get_data(as_text=True))
    res = client.post("/admin/verify-otp", data={"otp_code": code, "csrf_token": token})

    assert res.status_code == 200
    with client.session_transaction() as sess:
        assert sess.get("admin_id") == admin_user.id


def test_wrong_otp_code_rejected(client, admin_user, monkeypatch):
    _login_step_one(client, monkeypatch)

    otp_page = client.get("/admin/verify-otp")
    token = extract_csrf_token(otp_page.get_data(as_text=True))
    res = client.post("/admin/verify-otp", data={"otp_code": "000000", "csrf_token": token})

    assert res.status_code == 401
    with client.session_transaction() as sess:
        assert "admin_id" not in sess


def test_dashboard_requires_auth(client):
    res = client.get("/admin/dashboard")
    assert res.status_code == 302
    assert "/admin/login" in res.headers["Location"]


def test_admin_api_requires_auth_returns_401(client):
    res = client.get("/admin/api/customers")
    assert res.status_code == 401


def test_admin_crud_after_login(client, admin_user, monkeypatch, sample_payload):
    # Create via the public intake endpoint, then manage it via the
    # authenticated admin API - mirrors the real booth workflow.
    create_res = client.post("/api/customers", json=sample_payload)
    customer_id = create_res.get_json()["customer_id"]

    _full_login(client, monkeypatch)

    list_res = client.get("/admin/api/customers")
    assert list_res.status_code == 200
    assert list_res.get_json()["data"]["total"] == 1

    get_res = client.get(f"/admin/api/customers/{customer_id}")
    assert get_res.status_code == 200
    assert get_res.get_json()["data"]["customer_name"] == sample_payload["customer_name"]

    updated = dict(sample_payload)
    updated["customer_name"] = "Jane A. Doe"
    put_res = client.put(f"/admin/api/customers/{customer_id}", json=updated)
    assert put_res.status_code == 200
    assert put_res.get_json()["data"]["customer_name"] == "Jane A. Doe"

    del_res = client.delete(f"/admin/api/customers/{customer_id}")
    assert del_res.status_code == 200

    list_after_delete = client.get("/admin/api/customers")
    assert list_after_delete.get_json()["data"]["total"] == 0
