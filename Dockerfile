# Dockerfile
# ----------
# Bonus feature: containerized production image.
# Build:  docker build -t customer-management-system .
# Run:    docker run --env-file .env -p 8000:8000 customer-management-system
# (or use docker-compose.yml to run this alongside a PostgreSQL container)

FROM python:3.13-slim

WORKDIR /app

# Install OS packages needed to build psycopg2 (skipped if using
# psycopg2-binary, kept here in case you switch to psycopg2 later).
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=run.py \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "run:app"]
