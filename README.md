# Customer Management System

A production-oriented CRM backend and public intake form, built with
**Flask**, **SQLAlchemy**, **PostgreSQL/Supabase**, and
**Flask-Migrate**. The public side captures the full practice-intake
form (person, practice, pain point, and service interest) and enforces
phone/email duplicate rules; everything else - viewing, searching,
editing, deleting, and exporting customer records - lives behind an
authenticated, two-factor-protected Admin Dashboard (see section 5b).

This README documents every file, folder, class, and function in the
project, plus setup, testing, and deployment instructions. Use the
table of contents to jump to what you need.

> **New in v3.0** (Agentic Atoms branding, hero redesign, public
> dashboard removal, admin 2FA): the file-by-file breakdown in section
> 2 predates this revision's admin subsystem. For the full list of
> files added/changed in v3.0 and why, see `CHANGELOG.md` - it's kept
> more current than this section during fast-moving revisions.

## Table of Contents
1. [Project Structure](#1-project-structure)
2. [File-by-File, Class-by-Class Explanation](#2-file-by-file-class-by-class-explanation)
3. [Duplicate Validation Logic](#3-duplicate-validation-logic)
4. [API Reference & Response Format](#4-api-reference--response-format)
5. [PostgreSQL Setup](#5-postgresql-setup)
6. [Step-by-Step Installation Guide](#6-step-by-step-installation-guide)
7. [Database Migrations (Flask-Migrate)](#7-database-migrations-flask-migrate)
8. [Testing Instructions (Postman)](#8-testing-instructions-postman)
9. [Automated Tests (pytest)](#9-automated-tests-pytest)
10. [Expected Output Examples](#10-expected-output-examples)
11. [Security Notes](#11-security-notes)
12. [Docker](#12-docker)
13. [Deployment (Render / Railway)](#13-deployment-render--railway)
14. [Bonus Features Implemented](#14-bonus-features-implemented)
15. [Future Enhancements](#15-future-enhancements)

---

## 1. Project Structure

```
customer_management_system/
├── app/
│   ├── __init__.py            # Application factory (create_app)
│   ├── config.py               # Environment-driven configuration classes
│   ├── database.py             # Shared db (SQLAlchemy) + migrate (Flask-Migrate) instances
│   ├── models/
│   │   ├── __init__.py
│   │   └── customer.py         # Customer ORM model ("customers" table)
│   ├── routes/
│   │   ├── __init__.py
│   │   └── customer_routes.py  # REST API blueprint (/api/customers/*)
│   ├── services/
│   │   ├── __init__.py
│   │   └── customer_service.py # Business logic (duplicate checks, CRUD, stats, CSV export)
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── validators.py        # Server-side input validation
│   │   ├── responses.py         # Standard JSON response envelope helpers
│   │   └── logging_config.py    # Bonus: production-style logging setup
│   ├── templates/
│   │   └── index.html            # Intake form + records dashboard (single page)
│   └── static/
│       ├── css/style.css          # Styling (matches the provided UI reference)
│       └── js/script.js            # Form handling, chips, table, search/filter/pagination
│
├── migrations/
│   └── README.md                   # Explains how `flask db init` populates this folder
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Pytest fixtures (app/client/sample payload)
│   └── test_customers_api.py        # Integration tests, incl. all 4 duplicate scenarios
│
├── requirements.txt
├── run.py                            # Entry point (`python run.py`, `flask` CLI, gunicorn)
├── schema.sql                          # Raw PostgreSQL DDL, reference/manual setup
├── postman_collection.json             # Importable Postman collection (bonus)
├── Dockerfile                           # Bonus: container image
├── docker-compose.yml                    # Bonus: app + Postgres in one command
├── .dockerignore
├── .env.example
├── .gitignore
└── README.md                              # This file
```

---

## 2. File-by-File, Class-by-Class Explanation

### `run.py`
The entry point. `python run.py` starts the dev server; the `flask`
CLI (`flask db migrate`, `flask routes`, etc.) and gunicorn both
target this file (`run:app`). It just calls `create_app()` and runs it.

### `app/__init__.py` — `create_app(config_name=None)`
The **application factory**. Responsible for:
- Loading the right config class (`app/config.py`) for the environment.
- Wiring up logging (`app/utils/logging_config.py`).
- Binding SQLAlchemy and Flask-Migrate to this specific app instance.
- Importing `app.models.customer` so Alembic's autogenerate can see it.
- Registering the `customers_bp` blueprint.
- Defining `/` (serves the UI) and `/health` (liveness check).
- Installing JSON error handlers for 404 / 405 / 500, so API clients
  always get a consistent `{"success": false, "message": ...}` shape
  even for framework-level errors.

Using a factory instead of a bare `Flask(__name__)` at import time is
what makes `tests/conftest.py` possible — each test run gets its own,
freshly configured app instance rather than sharing global state.

### `app/config.py`
Three classes, all inheriting from a shared `Config` base:
- **`Config`** — reads `SECRET_KEY`, `DATABASE_URL`, and pagination
  defaults from environment variables (loaded from `.env` via
  `python-dotenv`).
- **`DevelopmentConfig`** — `DEBUG = True`.
- **`ProductionConfig`** — `DEBUG = False`; expects real secrets to be
  injected by the hosting platform.
- **`TestingConfig`** — points at a separate `TEST_DATABASE_URL` and
  disables CSRF for the test client.

`config_map` is a plain dict Flask's `app.config.from_object()` reads,
selected by the `FLASK_ENV` environment variable.

### `app/database.py`
Defines `db = SQLAlchemy()` and `migrate = Migrate()` with no app
bound yet. This one-line-per-object pattern is what lets
`app/models/customer.py` do `from app.database import db` without a
circular import back to `app/__init__.py`.

### `app/models/customer.py` — class `Customer(db.Model)`
The ORM model — the single source of truth for the `customers` table.
Columns map 1:1 to the schema in the spec (see `schema.sql` for the
raw DDL), plus one bonus column:
- `is_active` (Boolean, default `True`) — backs the soft-delete bonus
  feature; excluded from the literal requested schema but flagged
  clearly here and in `schema.sql`.

Methods:
- **`to_dict()`** — serializes a row into the JSON shape used by every
  API response. Centralizing this avoids each route hand-building
  its own dict (and forgetting a field).
- **`__repr__()`** — developer-friendly representation for logs/shells.

### `app/utils/validators.py` — `validate_customer_payload(data)`
Pure-Python (no Flask/SQLAlchemy import), so it's trivially unit
testable in isolation. Validates:
- Required fields present, non-empty after trimming whitespace
  (`customer_name`, `phone_number`, `email`, `business_name`,
  `specialty`, `pain_point`, `interested_service`).
- Optional text fields (`customer_role`, `additional_notes`) — length
  checked only if present.
- Email format via regex.
- Phone format (digits/spaces/`+`/`-`/`()` only) and a minimum digit count.
- Optional integer fields (`locations`, `daily_calls`) — must parse as
  a non-negative integer if provided, `None` if left blank.
- Every field's maximum length, matching the database column sizes
  exactly (`FIELD_LIMITS` dict), so a value that would fail the
  database's `VARCHAR(n)` constraint is caught here first with a
  clear message instead of surfacing as a raw database error.

Returns `(errors, cleaned)` — `errors` is empty on success; `cleaned`
holds trimmed/normalized values ready to pass straight into
`Customer(**cleaned)`.

### `app/utils/responses.py`
Three tiny helper functions that build the exact JSON envelope
requested in the spec:
- **`success_response(message, status_code=200, data=None, customer_id=None)`**
- **`error_response(message, status_code=400)`**
- **`validation_error_response(errors, status_code=400)`**

Every route calls one of these, so the response shape is guaranteed
consistent across the whole API.

### `app/utils/logging_config.py` — `configure_logging(app)`
Bonus feature. Attaches a stdout handler (captured automatically by
Docker/Render/Railway) and a rotating file handler under `logs/` for
local debugging. Both share one log-line format.

### `app/services/customer_service.py`
The business-logic layer, kept separate from HTTP routing so it's
directly unit-testable and so routes stay thin.

- **`DuplicateCustomerError`**, **`CustomerNotFoundError`** — plain
  `Exception` subclasses. The service layer raises these; the route
  layer is the only place that knows they map to HTTP 409 / 404.
- **`_find_duplicate(phone_number, email, exclude_id=None)`** — the
  heart of the duplicate-validation requirement (see
  [section 3](#3-duplicate-validation-logic) below).
- **`create_customer(cleaned)`** — checks for a duplicate, inserts a
  new `Customer`, commits, and catches `IntegrityError` as a race-
  condition safety net (in case two requests slip past the
  application-level check at the same instant).
- **`update_customer(customer_id, cleaned)`** — same duplicate check,
  excluding the row being updated itself.
- **`get_customer(customer_id)`** — simple lookup, raises
  `CustomerNotFoundError` if missing.
- **`list_customers(page, per_page, search, specialty, interested_service, include_inactive)`**
  — bonus search/filter/pagination in a single query.
- **`delete_customer(customer_id, hard=False)`** — bonus soft-delete
  (flip `is_active`) with an optional hard-delete path.
- **`get_statistics()`** — bonus dashboard aggregate: total active
  customers, grouped counts by specialty and by interested service.
- **`export_customers_csv(include_inactive=False)`** — bonus CSV export.

### `app/routes/customer_routes.py`
The Flask **Blueprint** (`customers_bp`, mounted at `/api/customers`).
Every route follows the same shape: parse/validate request → call a
service function → translate the result into a response helper.

| Route | Method | Purpose |
|---|---|---|
| `""` | POST | `create_customer()` — validate, call `service.create_customer`, return 201/400/409 |
| `""` | GET | `list_customers()` — parses `page`/`per_page`/`search`/`specialty`/`interested_service`/`include_inactive` query params |
| `"/stats"` | GET | `customer_stats()` — bonus dashboard endpoint |
| `"/export"` | GET | `export_customers()` — bonus CSV download |
| `"/<int:customer_id>"` | GET | `get_customer()` |
| `"/<int:customer_id>"` | PUT | `update_customer()` |
| `"/<int:customer_id>"` | DELETE | `delete_customer()` — `?hard=true` for a permanent delete |

### `app/templates/index.html`
Single-page UI: a brand panel (left) showing live stats, and a
form panel (right) with the five intake sections from the spec
(person / practice / business / service interest / additional notes),
followed by a records dashboard (search, specialty/service filters,
paginated table, CSV export link, and an expandable detail row per
customer).

### `app/static/css/style.css`
Dark, warm-amber theme (`#0A0908` background, `#E2900F` amber accent,
Fraunces/Inter/IBM Plex Mono type pairing) — the same visual language
as the uploaded Agentic Atoms reference form, extended with table,
toolbar, pagination, and stat-breakdown styling for the dashboard.

### `app/static/js/script.js`
All frontend behavior, no framework:
- Chip-group single-select logic for `pain_point` / `interested_service`.
- Form submit handler — posts JSON, shows field-level errors from
  `{"errors": {...}}` or a banner message from `{"message": ...}`.
- `loadStats()` — populates the live customer count + specialty
  breakdown in the brand panel.
- `loadCustomers(page)` — fetches the paginated/filtered/searched list
  and renders the table + pagination controls.
- Row click toggles an inline detail row (role, locations, calls/day,
  pain point, notes) without needing a modal.
- Delete button calls `DELETE /api/customers/<id>` with a confirm step.

### `tests/conftest.py` & `tests/test_customers_api.py`
See [section 9](#9-automated-tests-pytest).

### `schema.sql`
Raw DDL equivalent of `app/models/customer.py`, including a
`set_updated_at()` trigger so `updated_at` auto-updates even for rows
modified outside the Flask app (the ORM's `onupdate=` only fires for
writes made through SQLAlchemy).

### `Dockerfile` / `docker-compose.yml` / `.dockerignore`
See [section 12](#12-docker).

---

## 3. Duplicate Validation Logic

Implemented once, in `_find_duplicate()` inside
`app/services/customer_service.py`, and reused by both create and update:

1. Look up any existing row with the same `phone_number`.
2. Look up any existing row with the same `email`.
3. If **both** matches point to the same existing row →
   `"Customer already exists."` (HTTP 409)
4. Else if only the phone matches → `"Phone number already exists."` (409)
5. Else if only the email matches → `"Email already exists."` (409)
6. Otherwise → safe to insert/update; on success, respond
   `"Customer created successfully."` (201) with the new `customer_id`.

This is checked at the **application level** (for a clear, field-
specific message) and backed by **database-level `UNIQUE` constraints**
on `phone_number` and `email` — if two requests race each other,
PostgreSQL rejects the second insert and the code catches that
`IntegrityError`, reporting `"Customer already exists."` instead of a
500 error.

**Documented edge case:** if a phone number belongs to existing
customer A and the submitted email belongs to a *different* existing
customer B, the phone-number conflict is reported first. Adjust the
order inside `_find_duplicate()` if your business rules need a
different priority.

---

## 4. API Reference & Response Format

All responses are JSON with one of these three shapes:

**Success**
```json
{ "success": true, "message": "Customer created successfully.", "customer_id": 101, "data": { "...": "..." } }
```

**Duplicate / not-found / other business error**
```json
{ "success": false, "message": "This email or contact number is already registered." }
```

**Validation error**
```json
{ "success": false, "errors": { "email": "Enter a valid email address." } }
```

### Public API (no auth - intake only)

| Method | Path | Status codes |
|---|---|---|
| POST | `/api/customers` | 201 created, 400 validation error, 409 duplicate |
| GET | `/health` | 200 |

As of v3.0, this is the **entire** public API. There is no public way
to list, view, update, delete, or export customer records - see
"Public dashboard removed" in `CHANGELOG.md` if you're looking for
where `GET/PUT/DELETE /api/customers/*` went.

### Admin API (requires an authenticated admin session - see section 5b)

| Method | Path | Status codes |
|---|---|---|
| GET/POST | `/admin/login` | 200, 401 |
| GET/POST | `/admin/verify-otp` | 200, 401 |
| POST | `/admin/logout` | 200 |
| GET | `/admin/dashboard` | 200, 302 (redirect to login if not authenticated) |
| GET | `/admin/api/customers?page=&per_page=&search=&specialty=&interested_service=&include_inactive=` | 200, 401 |
| GET | `/admin/api/customers/stats` | 200, 401 |
| GET | `/admin/api/customers/export?include_inactive=` | 200 (CSV), 401 |
| GET | `/admin/api/customers/<id>` | 200, 401, 404 |
| PUT | `/admin/api/customers/<id>` | 200, 400, 401, 404, 409 |
| DELETE | `/admin/api/customers/<id>?hard=` | 200, 401, 404 |

---

## 5. PostgreSQL Setup

> **As of v2.1, this project runs against Supabase Postgres in
> production.** Section 5a below is the primary path — this section
> (5) is kept for local/self-hosted Postgres, which still works
> identically for local development if you prefer it over a hosted
> Supabase dev branch.

1. Install PostgreSQL 13+ if you don't already have it running.
2. Create the database and (optionally) a dedicated test database:
   ```bash
   psql -U postgres
   CREATE DATABASE customer_management;
   CREATE DATABASE customer_management_test;
   \q
   ```
3. Note the connection string format used throughout this project:
   ```
   postgresql+psycopg2://<user>:<password>@<host>:<port>/<database>
   ```

You do **not** need to run `schema.sql` by hand if you follow the
Flask-Migrate steps below — it's provided for reference/manual setup
only.

---

## 5a. Supabase Setup

This project's SQLAlchemy models, migrations, and CRUD logic are
**unchanged** for the Supabase migration — only the connection string
(and a small normalization helper in `app/config.py`) differ from
plain self-hosted Postgres.

1. **Create a Supabase project** at [supabase.com](https://supabase.com) →
   New Project → choose a name, database password, and region.
2. **Get the connection string**: in your project, go to
   *Project Settings → Database → Connection string → URI tab*.
   Copy the string — it looks like:
   ```
   postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
   ```
   Use the **Session pooler** (port `6543`) connection for normal app
   traffic; use the **direct connection** (port `5432`) only if your
   host has a stable, non-serverless connection to Supabase (direct
   connections don't work well from serverless/edge environments).
3. **Update your `.env`**:
   ```
   DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
   ```
   You do not need to add `+psycopg2` or `sslmode=require` yourself —
   `app/config.py`'s `_normalize_database_url()` adds both
   automatically when it detects a `supabase.co` host.
4. **Run migrations against Supabase** (same commands as any other
   Postgres target):
   ```bash
   flask db init        # first time only
   flask db migrate -m "create customers table"
   flask db upgrade
   ```
   If you're upgrading an existing v2.0 database (already migrated
   once) rather than starting fresh, just run:
   ```bash
   flask db migrate -m "add practice_type fields, widen interested_service"
   flask db upgrade
   ```
   to pick up this patch's two schema changes (see `CHANGELOG.md`).
5. **Test the connection**:
   ```bash
   python run.py
   curl http://127.0.0.1:5000/health
   curl -X POST http://127.0.0.1:5000/api/customers -H "Content-Type: application/json" -d '{"customer_name":"Dr. Jane Doe","phone_number":"5551234567","email":"jane@example.com","business_name":"Doe Family Practice","practice_type":"Medical Practice","specialty":"Family Medicine","pain_point":"High call volume","interested_service":"AI Receptionist"}'
   ```
   A `201` response with a `customer_id` confirms the app is writing
   to Supabase correctly. Re-run the same request to confirm duplicate
   validation still returns `"This email or contact number is already
   registered."` (409).
6. **Verify existing functionality still works**: duplicate
   validation and create were re-tested against the new duplicate-
   check logic and field set (`tests/test_customers_api.py`); list,
   get, update, and delete moved to the authenticated admin API as of
   v3.0 and are covered by `tests/test_admin_routes.py` instead - see
   section 5b below to set up admin access.

---

## 5b. Admin 2FA Setup

As of v3.0, customer records are no longer publicly viewable -
everything beyond submitting the intake form (viewing, searching,
editing, deleting, exporting) requires signing in to `/admin/login`
with a password **and** an emailed one-time code.

1. **Run migrations** so the `admin_users` table exists (see section 7
   below) - it's a new table added in this revision, alongside the
   `practice_type`/`practice_type_other` columns from v2.1.
2. **Create the first admin account** via the CLI (never over HTTP -
   this is deliberate, so account creation stays an operator action):
   ```bash
   flask create-admin
   ```
   You'll be prompted for a username, an email (where OTP codes are
   sent), and a password (hidden as you type).
3. **Configure OTP email delivery** in `.env` (see the "Admin 2FA"
   block in `.env.example`):
   ```
   SMTP_HOST=smtp.yourprovider.com
   SMTP_PORT=587
   SMTP_USER=your-smtp-username
   SMTP_PASSWORD=your-smtp-password
   OTP_FROM_EMAIL=no-reply@agenticatoms.com
   ```
   Leave `SMTP_HOST` blank during local development - OTP codes are
   written to `logs/app.log` (and the console) instead, so you can
   test the full login flow without a real mailbox.
4. **Log in**: go to `/admin/login`, enter your credentials, then
   check your email (or `logs/app.log` in dev) for the 6-digit code
   and enter it on the next screen. Codes expire after 10 minutes
   (configurable via `OTP_VALIDITY_MINUTES`) and allow 5 attempts.
5. **Manage customers** from `/admin/dashboard` - search, filter by
   specialty/service, paginate, view/edit/delete individual records,
   and export to CSV, all behind that same session.

---

## 6. Step-by-Step Installation Guide

```bash
# 1. Get the code and enter the project
cd customer_management_system

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# then edit .env: SECRET_KEY, DATABASE_URL, TEST_DATABASE_URL

# 5. Initialize and apply database migrations (see section 7)
flask db init
flask db migrate -m "create customers table"
flask db upgrade

# 6. Run the app
python run.py
# -> http://127.0.0.1:5000
```

For production, run behind gunicorn instead of the dev server:
```bash
export FLASK_ENV=production
gunicorn -w 4 -b 0.0.0.0:8000 "run:app"
```

---

## 7. Database Migrations (Flask-Migrate)

This project uses Flask-Migrate (Alembic under the hood) instead of
`db.create_all()`, so schema changes are versioned:

```bash
flask db init                              # once, creates migrations/
flask db migrate -m "create customers table"  # autogenerate a migration from the model
flask db upgrade                            # apply it to the database
```

Whenever you change `app/models/customer.py` later, repeat the
`migrate` + `upgrade` steps to generate and apply a new versioned
migration. See `migrations/README.md` for why this folder ships empty.

---

## 8. Testing Instructions (Postman)

1. Import **`postman_collection.json`** into Postman
   (File → Import → select the file).
2. Set the collection variable `base_url` if your app isn't running
   on `http://127.0.0.1:5000`.
3. Start the Flask app (`python run.py`).
4. Run the requests in order:
   1. **Create customer (success)** → expect `201` and a `customer_id`.
   2. **Missing required fields** → expect `400` with an `errors` object.
   3. **Duplicate phone, different email** → expect `409`, `"Phone number already exists."`
   4. **Duplicate email, different phone** → expect `409`, `"Email already exists."`
   5. **Same phone AND email** → expect `409`, `"Customer already exists."`
   6. **List customers** → expect `200` with pagination metadata.
   7. **Get / Update / Delete by ID** → set the `customer_id` collection
      variable to the ID returned by request #1 first.
   8. **Statistics** and **Export CSV** — bonus endpoints.

---

## 9. Automated Tests (pytest)

```bash
pytest -v
```

`tests/conftest.py` spins up the app in `TestingConfig` (pointed at
`TEST_DATABASE_URL`), creates all tables fresh before each test, and
drops them afterward — so tests never touch your real data.
`tests/test_customers_api.py` covers all 4 duplicate scenarios, basic
CRUD, validation errors, and the soft-delete/`include_inactive` bonus
behavior.

> **Sandbox note:** these tests require a real, reachable PostgreSQL
> instance (via `TEST_DATABASE_URL`) — they're integration tests
> against actual database constraints, not mocked. I validated the
> pure-Python pieces (`app/utils/validators.py`) directly in an
> offline sandbox with no network access and no PostgreSQL available,
> and confirmed all 7 validation scenarios pass. I could not execute
> `pytest` itself or start the live server end-to-end in that same
> sandbox, since `Flask-SQLAlchemy`, `Flask-Migrate`, and `psycopg2`
> aren't installable without network access there. Please run
> `pytest -v` yourself after `pip install -r requirements.txt` against
> a real Postgres instance to confirm the full integration path.

---

## 10. Expected Output Examples

Actual screenshots require a running instance with a real browser and
database, which isn't available in the environment this project was
authored in — the JSON examples below are what each scenario returns
in practice (also runnable directly via the Postman collection).

**`POST /api/customers` — success (201)**
```json
{
  "success": true,
  "message": "Customer created successfully.",
  "customer_id": 101,
  "data": {
    "customer_id": 101,
    "customer_name": "Jane Doe",
    "customer_role": "Owner",
    "phone_number": "5551234567",
    "email": "jane@example.com",
    "business_name": "Doe Dental",
    "specialty": "Dental",
    "locations": 2,
    "pain_point": "Too many missed calls",
    "daily_calls": 45,
    "interested_service": "ARIA AI",
    "additional_notes": "Currently using a basic answering service.",
    "is_active": true,
    "created_at": "2026-07-23T09:00:00Z",
    "updated_at": "2026-07-23T09:00:00Z"
  }
}
```

**Duplicate phone, different email (409)**
```json
{ "success": false, "message": "Phone number already exists." }
```

**Validation error (400)**
```json
{
  "success": false,
  "errors": {
    "customer_name": "Customer name is required.",
    "email": "Email is required."
  }
}
```

---

## 11. Security Notes

- **SQL injection** — every query goes through the SQLAlchemy ORM
  (`Customer.query.filter_by(...)`, `db.session.add(...)`), which
  always parameterizes values. No raw string-concatenated SQL exists
  anywhere in the codebase.
- **Server-side validation** — every write endpoint re-validates via
  `app/utils/validators.py`, regardless of what the frontend already
  checked.
- **Database-level constraints** — `UNIQUE` on `phone_number` and
  `email` guarantee duplicates can't slip through under concurrent
  requests, even if a future API client skips validation entirely.
- **Secrets** — `SECRET_KEY` and `DATABASE_URL` are read from the
  environment; `.env` is excluded via `.gitignore`.
- **CSRF** — Flask-WTF is included in `requirements.txt` for CSRF
  protection **if you add a traditional (non-JSON) HTML form post**
  later. As shipped, the UI submits JSON via `fetch()` to a same-
  origin JSON API, which is the standard modern pattern and doesn't
  use session-cookie-based form submission — CSRF tokens apply to
  cookie-authenticated HTML form posts, not to this API's request
  style. If you add cookie-based session auth later, wire up
  `CSRFProtect(app)` and a token field at that point.
- **Output encoding** — the frontend escapes all customer-supplied
  values before inserting them into the DOM (`escapeHtml()` in
  `script.js`) to prevent stored/reflected XSS in the records table.
- **Graceful error handling** — `IntegrityError` (race conditions) and
  generic 404/405/500s all return structured JSON, never a raw
  traceback or stack trace to the client.

---

## 12. Docker

```bash
cp .env.example .env      # edit as needed
docker compose up --build
```

This starts a PostgreSQL 16 container and the Flask app together
(via gunicorn), reachable at `http://localhost:8000`. The Postgres
data persists in the `customer_db_data` named volume across restarts.

To build/run the app image standalone (against an external database):
```bash
docker build -t customer-management-system .
docker run --env-file .env -p 8000:8000 customer-management-system
```

---

## 13. Deployment (Render / Railway)

Both platforms follow the same basic pattern:

1. Push this project to a GitHub repository.
2. Create a new **PostgreSQL** instance on the platform first, and
   copy its connection string.
3. Create a new **Web Service** (Render) or **Service** (Railway)
   pointing at your repo.
4. Set environment variables in the platform's dashboard:
   `FLASK_ENV=production`, `SECRET_KEY=<generate one>`,
   `DATABASE_URL=<the connection string from step 2>`.
5. Set the build command: `pip install -r requirements.txt`.
6. Set the start command: `gunicorn -w 4 -b 0.0.0.0:$PORT run:app`.
7. After the first deploy, run migrations once via the platform's
   shell/console: `flask db upgrade`.

---

## 14. Bonus Features Implemented

- ✅ Search customers (name, business, email, phone)
- ✅ Filter by specialty
- ✅ Filter by interested service
- ✅ Pagination (`page` / `per_page`, capped by `MAX_PAGE_SIZE`)
- ✅ Statistics endpoint (`/api/customers/stats`) + live dashboard panel
- ✅ CSV export (`/api/customers/export`)
- ✅ Soft delete (`is_active` flag, with an opt-in hard-delete path)
- ✅ Update history (`updated_at`, auto-maintained by the ORM and a
  matching database trigger for non-ORM writes)
- ✅ Logging (stdout + rotating file handler)
- ✅ Docker support (`Dockerfile` + `docker-compose.yml`)
- ✅ Unit/integration tests (`pytest`, see section 9)
- ✅ GitHub-ready structure (`.gitignore`, `.dockerignore`, no secrets committed)
- ✅ Deployment instructions for Render/Railway (section 13)

---

## 15. Future Enhancements

- **Authentication & authorization** — no login exists yet; add
  Flask-Login or JWT auth before handling real customer data.
- **Rate limiting** — Flask-Limiter on the `POST`/`PUT` endpoints.
- **Phone/email normalization** — e.g. consistent E.164 phone
  formatting, so `(555) 123-4567` and `555-123-4567` are recognized
  as the same number for duplicate-checking purposes.
- **Structured "Other" follow-up fields** — the intake form's `chip`
  fields (`pain_point`, `interested_service`) currently store "Other"
  as a literal string; a natural enhancement is a follow-up free-text
  input that appears when "Other" is selected.
- **Audit trail** — track which user made each change, once
  authentication exists.
- **Async CSV export** — for very large customer lists, move export
  to a background task/queue rather than generating it synchronously.
