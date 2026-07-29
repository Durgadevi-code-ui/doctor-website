"""
app/models/customer.py
-----------------------
SQLAlchemy ORM model for the `customers` table. This is the single
source of truth for the schema; `schema.sql` is the equivalent raw
DDL kept for reference, and `migrations/` (Flask-Migrate/Alembic)
tracks schema changes to this model over time.

Field set mirrors every relevant field from the Agentic Atoms practice
intake form reference, grouped by the same five sections used in the
UI: person info, practice info, business info, service interest, and
additional notes.
"""

from datetime import datetime

from app.database import db


class Customer(db.Model):
    __tablename__ = "customers"

    # --- Identity ---
    customer_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)

    # --- Section 1: Person information ---
    customer_name = db.Column(db.String(150), nullable=False)
    customer_role = db.Column(db.String(100), nullable=True)
    phone_number = db.Column(db.String(20), nullable=False, unique=True, index=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)

    # --- Section 2: Practice information ---
    business_name = db.Column(db.String(200), nullable=False)
    # practice_type / practice_type_other: added for the Washington DC
    # Doctors Meet intake revision (see CHANGELOG.md). practice_type_other
    # only holds a value when practice_type == "Other".
    practice_type = db.Column(db.String(100), nullable=True)
    practice_type_other = db.Column(db.String(150), nullable=True)
    specialty = db.Column(db.String(100), nullable=True)
    locations = db.Column(db.Integer, nullable=True)

    # --- Section 3: Business information ---
    pain_point = db.Column(db.Text, nullable=True)
    daily_calls = db.Column(db.Integer, nullable=True)

    # --- Section 4: Service interest ---
    # Widened from 100 -> 255 chars: this field now stores a
    # comma-joined list from the multi-select checkbox UI (e.g.
    # "AI Receptionist, AI Chatbot, Custom App, Website Enhancement")
    # instead of a single chip value.
    interested_service = db.Column(db.String(255), nullable=True)

    # --- Section 5: Additional information ---
    additional_notes = db.Column(db.Text, nullable=True)

    # --- Bonus: soft delete flag (see README "Bonus Features") ---
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # --- Timestamps ---
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def to_dict(self):
        """Serialize the row into a JSON-friendly dict for API responses."""
        return {
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "customer_role": self.customer_role,
            "phone_number": self.phone_number,
            "email": self.email,
            "business_name": self.business_name,
            "practice_type": self.practice_type,
            "practice_type_other": self.practice_type_other,
            "specialty": self.specialty,
            "locations": self.locations,
            "pain_point": self.pain_point,
            "daily_calls": self.daily_calls,
            "interested_service": self.interested_service,
            "additional_notes": self.additional_notes,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
            "updated_at": self.updated_at.isoformat() + "Z" if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Customer {self.customer_id}: {self.customer_name} ({self.business_name})>"
