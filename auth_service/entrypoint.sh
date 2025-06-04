#!/usr/bin/env bash
set -e

# 1) Wait for DB to be ready (TCP port check)
until </dev/tcp/auth-postgres/5432; do
  echo "Waiting for Postgres..."
  sleep 1
done

# 2) Create tables (idempotent)
python /auth_service/app/db/create_tables.py

# 3) Run tests
cd /auth_service/
pytest -vv -s # verbose and including all print statements

echo "Running test suite..."
pytest --maxfail=1 --disable-warnings -q || {
  echo "Tests failed; exiting."
  exit 1
}
echo "Tests passed; starting application..."

# 4) Start the service
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
