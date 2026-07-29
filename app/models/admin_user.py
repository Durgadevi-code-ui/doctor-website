"""
app/models/admin_user.py
--------------------------
ORM model backing the secure Admin Dashboard's authentication.

Added for the Washington DC Doctors Meet security revision - see
CHANGELOG.md, "Security & Admin Dashboard". This is a new model (new
table), not a change to the existing Customer model, so it has zero
effect on existing customer data or the public intake API.

Password hashing uses werkzeug.security (already a Flask dependency -
no new package required). The one-time password (OTP) used for the
second authentication factor is itself stored hashed, never in plain
text, and is time-limited.
"""

import secrets
from datetime import datetime, timedelta

from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

from app.database import db

OTP_VALIDITY_MINUTES = 10  # fallback default if OTP_VALIDITY_MINUTES isn't set in config
OTP_MAX_ATTEMPTS = 5


class AdminUser(db.Model):
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), nullable=False, unique=True, index=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # --- Second factor (email OTP) ---
    otp_code_hash = db.Column(db.String(255), nullable=True)
    otp_expires_at = db.Column(db.DateTime, nullable=True)
    otp_attempts = db.Column(db.Integer, nullable=False, default=0)

    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)

    # --- Password (factor 1) ---
    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    # --- OTP (factor 2) ---
    def issue_otp(self):
        """
        Generates a new 6-digit OTP, stores only its hash (plus an
        expiry and a reset attempt counter), and returns the PLAIN
        code so the caller can email it. The plain code is never
        persisted anywhere.
        """
        code = f"{secrets.randbelow(1_000_000):06d}"
        self.otp_code_hash = generate_password_hash(code)
        validity_minutes = current_app.config.get("OTP_VALIDITY_MINUTES", OTP_VALIDITY_MINUTES)
        self.otp_expires_at = datetime.utcnow() + timedelta(minutes=validity_minutes)
        self.otp_attempts = 0
        return code

    def verify_otp(self, submitted_code):
        """
        Returns True and clears the OTP on success. Returns False on a
        wrong code, an expired code, or too many attempts - and
        increments the attempt counter either way so a submitted code
        can only be guessed OTP_MAX_ATTEMPTS times.
        """
        if not self.otp_code_hash or not self.otp_expires_at:
            return False
        if datetime.utcnow() > self.otp_expires_at:
            return False
        if self.otp_attempts >= OTP_MAX_ATTEMPTS:
            return False

        self.otp_attempts += 1
        if check_password_hash(self.otp_code_hash, submitted_code):
            self.otp_code_hash = None
            self.otp_expires_at = None
            self.otp_attempts = 0
            return True
        return False

    def __repr__(self):
        return f"<AdminUser {self.id}: {self.username}>"
