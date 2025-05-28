#!/usr/bin/env bash
set -e

# 1) Wait for DB to be ready (TCP port check)
until </dev/tcp/risk-postgres/5432; do
  echo "Waiting for Postgres..."
  sleep 1
done

# 2) Create tables (idempotent)
python /risk_engine/app/db/create_tables.py

# 3) Start the service
exec uvicorn app.main:app --host 0.0.0.0 --port 8001
