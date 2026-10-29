#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python ]]; then
  printf '%s\n' 'Project Python environment is missing. Install uv, then run `uv sync --frozen --python 3.12 --no-dev` from the project directory.' >&2
  if [[ ! -f frontend/dist/index.html ]]; then
    printf '%s\n' 'Built frontend is missing. Run `npm --prefix frontend ci && npm --prefix frontend run build` from the project directory.' >&2
  fi
  printf '%s\n' 'See docs/startup.md for the complete source setup instructions.' >&2
  exit 2
fi
exec .venv/bin/python -m backend.workbench.launcher
