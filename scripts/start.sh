#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --frozen --python 3.12 --no-dev
exec .venv/bin/python -m uvicorn backend.workbench.main:app --host 127.0.0.1 --port "${CRW_PORT:-8765}" --no-access-log
