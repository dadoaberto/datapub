#!/bin/bash
set -e
set -o pipefail

echo "[ENTRYPOINT] Initializing entrypoint..."

echo "[DEBUG] Environment:"
echo "  - DATABASE_URL: ${DATABASE_URL%%@*}"
echo "  - NEO4J_URL: ${NEO4J_URL%%@*}" 
echo "  - PYTHONPATH: $PYTHONPATH"
echo "  - WORKDIR: $(pwd)"

if ! command -v python &> /dev/null; then
    echo "[ERRO] Python is not installed."
    exit 1
fi

VENV_PATH="/app/.venv"
if [[ -f "$VENV_PATH/bin/activate" ]]; then
    echo "[INFO] Ativando virtualenv..."
    source "$VENV_PATH/bin/activate"
    echo "[INFO] Python path: $(which python)"
fi

if [[ "$1" == "run-migrations" ]]; then
    echo "[INFO] Executando migrações..."
    python -m alembic upgrade head
    exit 0
fi

echo "[INFO] Exec command: $@"
exec "$@"
