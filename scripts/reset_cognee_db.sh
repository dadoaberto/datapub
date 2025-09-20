#!/usr/bin/env bash
set -euo pipefail

# Reseta o banco do Cognee (cognee_db) no Postgres do compose
# Uso:
#   docker-compose run --rm datapub bash -lc ./scripts/reset_cognee_db.sh

DB_HOST=${DB_HOST:-postgres}
DB_PORT=${DB_PORT:-5432}
DB_USERNAME=${DB_USERNAME:-cognee}
DB_PASSWORD=${DB_PASSWORD:-cognee}
DB_NAME=${DB_NAME:-cognee_db}

export PGPASSWORD="$DB_PASSWORD"

echo "[reset_cognee_db] Dropping database $DB_NAME (if exists) ..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USERNAME" -d postgres -v ON_ERROR_STOP=1 -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME';" || true
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USERNAME" -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS \"$DB_NAME\";"

echo "[reset_cognee_db] Creating database $DB_NAME ..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USERNAME" -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE \"$DB_NAME\" OWNER \"$DB_USERNAME\";"

echo "[reset_cognee_db] Ensuring pgvector extension ..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USERNAME" -d "$DB_NAME" -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo "[reset_cognee_db] Done."

