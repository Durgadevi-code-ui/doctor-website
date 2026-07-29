"""
tests/conftest.py
-------------------
Shared pytest fixtures.

Requires a real, reachable PostgreSQL database configured via
TEST_DATABASE_URL (see .env.example) - these are integration tests
against the actual database driver/constraints (e.g. the UNIQUE
constraint race-condition safety net), not mocked-out unit tests.

Run with:
    pytest
"""

import pytest

from app import create_app
from app.database import db as _db


@pytest.fixture()
def app():
    application = create_app("testing")

    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def sample_payload():
    return {
        "customer_name": "Jane Doe",
        "customer_role": "Doctor",
        "phone_number": "5551234567",
        "email": "jane@example.com",
        "business_name": "Doe Dental",
        "practice_type": "Dental Practice",
        "specialty": "Dentist",
        "locations": 2,
        "pain_point": "Too many missed calls",
        "daily_calls": 45,
        "interested_service": "AI Receptionist, AI Chatbot",
        "additional_notes": "Currently using a basic answering service.",
    }


@pytest.fixture()
def admin_user(app):
    """Creates a known admin account (username: testadmin / password:
    Testpass123!) for the admin auth tests in tests/test_admin_routes.py."""
    from app.models.admin_user import AdminUser

    admin = AdminUser(username="testadmin", email="admin@example.com")
    admin.set_password("Testpass123!")
    _db.session.add(admin)
    _db.session.commit()
    return admin


def extract_csrf_token(html):
    """Pulls the csrf_token hidden-input value out of a rendered admin
    auth page, so tests can submit a valid token like a real browser
    would (see app/routes/admin_routes.py, _check_csrf())."""
    import re

    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "csrf_token input not found in rendered page"
    return match.group(1)
