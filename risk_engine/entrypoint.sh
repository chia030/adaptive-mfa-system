#!/usr/bin/env bash
set -e

# 1) Wait for DB to be ready (TCP port check)
until </dev/tcp/risk-postgres/5432; do
  echo "Waiting for Postgres..."
  sleep 1
done

# 2) Create tables (idempotent)
python /risk_engine/app/db/create_tables.py

# 3) Wait for RabbitMQ connection (TCP port check)
until </dev/tcp/rabbitmq/4369; do 
  echo "Waiting for RabbitMQ..."
  sleep 1
done

# 4) Run tests
cd /risk_engine/
# pytest -vv -s # verbose and including all print statements

echo "Running test suite..."
pytest -vv -s --maxfail=1 --disable-warnings -q || {
  echo "Tests failed; exiting."
  exit 1
}
echo "Tests passed; starting application..."

# 5) Start the service
exec uvicorn app.main:app --host 0.0.0.0 --port 8001
