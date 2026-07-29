# migrations/

This folder is intentionally empty in the delivered project.

Flask-Migrate (Alembic) generates its real contents on your machine,
against your actual database connection, the first time you run:

```bash
flask db init
```

That command creates `alembic.ini`, `env.py`, `script.py.mako`, and a
`versions/` subfolder here. From then on:

```bash
flask db migrate -m "create customers table"
flask db upgrade
```

...generates and applies versioned migration files whenever
`app/models/customer.py` changes.

This is deliberately not pre-generated in the delivered project
because Alembic's `env.py` embeds a live connection/reflection step
tied to whichever database you actually run it against - shipping a
pre-baked migrations folder from a different environment risks
producing a migration history that doesn't match your database.
See README.md, section "Database Migrations (Flask-Migrate)", for the
full walkthrough.
