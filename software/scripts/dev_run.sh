#!/usr/bin/env bash
set -euo pipefail

# Project root = two levels up from this script (scripts/ → software/ → majong/)
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

VENV="$PROJECT_ROOT/software/.venv"

if [ ! -d "$VENV" ]; then
  echo "Creating venv..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -r software/requirements.txt
fi

echo "Starting server at http://0.0.0.0:8000  (local: http://localhost:8000)"
# Use --reload-dir to ONLY watch source code directories (never .venv / node_modules)
"$VENV/bin/uvicorn" software.web.app:app --host 0.0.0.0 --reload --port 8000 \
  --reload-dir software/web \
  --reload-dir software/services \
  --reload-dir software/orchestrator \
  --reload-dir software/adapters
