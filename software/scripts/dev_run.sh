#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  echo "Creating venv..."
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi

echo "Starting server at http://localhost:8000"
.venv/bin/uvicorn software.web.app:app --reload --port 8000
