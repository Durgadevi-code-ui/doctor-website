"""
app/database.py
----------------
Shared Flask extension instances.

`db` (SQLAlchemy), `migrate` (Flask-Migrate/Alembic), and `limiter`
(Flask-Limiter, added for the Washington DC Doctors Meet security
revision - see CHANGELOG.md) are all created here with no app attached
yet. They get bound to the real Flask app inside `app/__init__.py` via
`db.init_app(app)` / `migrate.init_app(app, db)` / `limiter.init_app(app)`.

Keeping this in its own module (instead of inside `app/__init__.py`)
is what lets `app/models/customer.py` and route modules import these
shared objects without a circular import back to the application
factory.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
migrate = Migrate()

# Default limit applies to any route not given its own @limiter.limit(...);
# admin login/OTP and the public intake endpoint set tighter limits
# directly on their routes (see app/routes/admin_routes.py and
# app/routes/customer_routes.py).
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per hour"])
