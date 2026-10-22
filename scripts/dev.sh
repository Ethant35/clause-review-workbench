#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --frozen --python 3.12
(cd frontend && npm ci)
.venv/bin/python -m uvicorn backend.workbench.main:app --host 127.0.0.1 --port 8765 --no-access-log &
backend_pid=$!
trap 'kill "$backend_pid" 2>/dev/null || true' EXIT INT TERM
(cd frontend && npm run dev)
