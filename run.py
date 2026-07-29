"""
run.py
------
Local/production entry point.

- `python run.py` starts the Flask dev server directly.
- The `flask` CLI (flask db init / migrate / upgrade, flask routes,
  etc.) discovers the app through this file via FLASK_APP=run.py
  (already set in .env.example).
- A production WSGI server points at this module too, e.g.:
      gunicorn -w 4 -b 0.0.0.0:8000 "run:app"
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=app.config.get("DEBUG", False))
