#!/usr/bin/env bash
set -e

# 1) Wait for DB to be ready (TCP port check)
until </dev/tcp/auth-postgres/5432; do
  echo "Waiting for Postgres..."
  sleep 1
done

# 2) Create tables (idempotent)
python /auth_service/app/db/create_tables.py

# 3) Wait for Risk Engine to be ready (TCP port check)
until </dev/tcp/risk-engine/8001; do
  echo "Waiting for Risk Engine..."
  sleep 1
done

# 4) Wait for MFA Handler to be ready (TCP port check)
until </dev/tcp/mfa-handler/8002; do
  echo "Waiting for MFA Handler..."
  sleep 1
done

# 5) Run tests
cd /auth_service/
# pytest -vv -s # verbose and including all print statements

echo "Running test suite..."
pytest -vv -s --maxfail=1 --disable-warnings -q || {
  echo "Tests failed; retrying..."
  sleep 1
  pytest -vv -s --maxfail=1 --disable-warnings -q || {
    echo "Tests failed; retrying..."
    sleep 1
    pytest -vv -s --maxfail=1 --disable-warnings -q || {
      echo "Tests failed; exiting."
      exit 1
    }
  }
}
echo "Tests passed; starting application..."

# 6) Start the service
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
