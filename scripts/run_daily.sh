#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DATE="${1:-$(date +%F)}"

cd "$PROJECT_ROOT"
mkdir -p logs

if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
else
  echo "[ERROR] Python binary not found (.venv/bin/python or python3)." >&2
  exit 1
fi

"$PYTHON_BIN" -m src.app.main --date "$RUN_DATE" >> logs/cron.log 2>&1
