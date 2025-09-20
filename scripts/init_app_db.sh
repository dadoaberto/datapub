#!/usr/bin/env bash
set -euo pipefail

echo "[init_app_db] Using APP_DATABASE_URL=${APP_DATABASE_URL:-}"
if [[ -z "${APP_DATABASE_URL:-}" ]]; then
  echo "APP_DATABASE_URL is not set. Export it or define it in docker-compose env for 'datapub'." >&2
  exit 1
fi

python - << 'PY'
import os
import sys
from sqlalchemy.engine.url import make_url
import psycopg

app_url = os.environ["APP_DATABASE_URL"]
url = make_url(app_url)

user = url.username
password = url.password or ""
host = url.host or "localhost"
port = url.port or 5432
dbname = url.database

# Connect to default 'postgres' DB to ensure target DB exists
conninfo = f"host={host} port={port} user={user} password={password} dbname=postgres"
try:
    with psycopg.connect(conninfo, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
            exists = cur.fetchone() is not None
            if not exists:
                try:
                    cur.execute(f"CREATE DATABASE \"{dbname}\" OWNER \"{user}\"")
                    print(f"[init_app_db] Created database {dbname}")
                except Exception as e:
                    # Handle collation version mismatch by refreshing template DBs and retry
                    msg = str(e)
                    print(f"[init_app_db] CREATE DATABASE failed: {msg}. Attempting REFRESH COLLATION VERSION on templates...")
                    try:
                        cur.execute("ALTER DATABASE template1 REFRESH COLLATION VERSION")
                    except Exception as e2:
                        print(f"[init_app_db] template1 refresh failed: {e2}")
                    try:
                        cur.execute("ALTER DATABASE template0 REFRESH COLLATION VERSION")
                    except Exception as e3:
                        print(f"[init_app_db] template0 refresh failed: {e3}")
                    cur.execute(f"CREATE DATABASE \"{dbname}\" OWNER \"{user}\"")
                    print(f"[init_app_db] Created database {dbname} after refreshing collations")
            else:
                print(f"[init_app_db] Database {dbname} already exists")
except Exception as e:
    print(f"[init_app_db] Failed ensuring database: {e}", file=sys.stderr)
    sys.exit(1)
PY

alembic upgrade head
echo "[init_app_db] Migration complete."

if [[ "${SEED_IBGE:-false}" == "true" ]]; then
  echo "[init_app_db] Seeding IBGE states/municipalities..."
  python - << 'PY'
from datapub.etl.ibge_localidades import run_sync_ibge
res = run_sync_ibge()
print(f"Seed result: {res}")
PY
fi
