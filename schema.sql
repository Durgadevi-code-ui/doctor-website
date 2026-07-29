-- schema.sql
-- -----------
-- Raw PostgreSQL DDL, equivalent to what Flask-Migrate/SQLAlchemy
-- generates from app/models/customer.py. Provided for manual setup,
-- review, or feeding into tooling outside the Python app.
--
-- In normal use you do NOT run this by hand - use Flask-Migrate
-- instead (see README "Database Migrations"), which tracks every
-- schema change as a versioned migration file.

CREATE TABLE IF NOT EXISTS customers (
    customer_id          BIGSERIAL PRIMARY KEY,

    -- Section 1: person information
    customer_name        VARCHAR(150) NOT NULL,
    customer_role         VARCHAR(100),
    phone_number          VARCHAR(20)  NOT NULL UNIQUE,
    email                 VARCHAR(255) NOT NULL UNIQUE,

    -- Section 2: practice information
    business_name         VARCHAR(200) NOT NULL,
    practice_type          VARCHAR(100),
    practice_type_other    VARCHAR(150),
    specialty              VARCHAR(100),
    locations              INTEGER,

    -- Section 3: business information
    pain_point             TEXT,
    daily_calls             INTEGER,

    -- Section 4: service interest
    -- Widened 100 -> 255: now stores a comma-joined multi-select
    -- list (e.g. "AI Receptionist, AI Chatbot") instead of one value.
    interested_service      VARCHAR(255),

    -- Section 5: additional information
    additional_notes         TEXT,

    -- Bonus: soft delete flag
    is_active                 BOOLEAN NOT NULL DEFAULT TRUE,

    -- Timestamps
    created_at                 TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_customers_phone_number ON customers (phone_number);
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers (email);
CREATE INDEX IF NOT EXISTS idx_customers_specialty ON customers (specialty);
CREATE INDEX IF NOT EXISTS idx_customers_is_active ON customers (is_active);

-- PostgreSQL has no built-in "auto-update on modification" for a
-- column - that behavior is implemented at the ORM level by
-- `onupdate=datetime.utcnow` in the SQLAlchemy model. The trigger
-- below reproduces the same behavior for anyone writing to this
-- table outside the Flask app (e.g. a direct SQL script).

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_customers_updated_at ON customers;
CREATE TRIGGER trg_customers_updated_at
    BEFORE UPDATE ON customers
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------- --
-- admin_users: added for the Washington DC Doctors Meet security
-- revision (see CHANGELOG.md). Backs the secure Admin Dashboard's
-- username+password + email-OTP two-factor login. Equivalent to
-- app/models/admin_user.py - create admin accounts via the
-- `flask create-admin` CLI command, not directly in SQL, so passwords
-- are always hashed correctly.
-- ---------------------------------------------------------------- --

CREATE TABLE IF NOT EXISTS admin_users (
    id                 SERIAL PRIMARY KEY,
    username           VARCHAR(80)  NOT NULL UNIQUE,
    email              VARCHAR(255) NOT NULL UNIQUE,
    password_hash      VARCHAR(255) NOT NULL,

    otp_code_hash      VARCHAR(255),
    otp_expires_at     TIMESTAMP,
    otp_attempts       INTEGER NOT NULL DEFAULT 0,

    is_active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at      TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_admin_users_username ON admin_users (username);
CREATE INDEX IF NOT EXISTS idx_admin_users_email ON admin_users (email);
