#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

root_dir="$PWD"
mkdir -p "$root_dir/artifacts/clean-readiness"
run_id="$(date -u +%Y%m%dT%H%M%SZ)-$$"
run_artifacts="$root_dir/artifacts/clean-readiness/$run_id"
mkdir -p "$run_artifacts"
clean_dir="$(mktemp -d "${TMPDIR:-/tmp}/crw-clean.XXXXXX")"
printf '%s\n' "$clean_dir/repo" > "$run_artifacts/clean-checkout-path.txt"
export CRW_PROCESS_REGISTRY="$run_artifacts/processes.json"

archive_artifacts() {
  local status=$?
  trap - EXIT
  if [[ -d "$clean_dir/repo/artifacts" ]]; then
    if ! cp -a "$clean_dir/repo/artifacts/." "$run_artifacts/"; then
      printf 'Could not preserve clean-checkout artifacts in %s\n' "$run_artifacts" >&2
      [[ $status -ne 0 ]] || status=1
    fi
  fi
  if [[ $status -eq 0 ]]; then
    printf 'Clean acceptance passed. Artifacts: %s\n' "$run_artifacts"
  else
    printf 'Clean acceptance failed (exit %s). Partial artifacts: %s\n' "$status" "$run_artifacts" >&2
  fi
  exit "$status"
}
trap archive_artifacts EXIT

git clone --no-local "$root_dir" "$clean_dir/repo"
cd "$clean_dir/repo"

# The floor check and test suites run in the same clean clone. All suites are
# sequential because their server processes share the run-scoped registry.
# Compare new work with the current qualified release; older release evidence
# was reviewed in its own release. Keep every floor rule unchanged.
node scripts/floor-guard.mjs --base v1.4.0
uv sync --frozen --python 3.12
npm --prefix frontend ci
npm --prefix frontend run build
.venv/bin/python -m playwright install chromium
.venv/bin/python -m pytest -q
.venv/bin/python tests/e2e.py
.venv/bin/python tests/adversarial_e2e.py
.venv/bin/python tests/interactions_e2e.py
.venv/bin/python tests/frontend_readiness_e2e.py
.venv/bin/python tests/frontend_state_e2e.py
.venv/bin/python tests/frontend_zoom_e2e.py
.venv/bin/python tests/upgrade_e2e.py --baseline v1.0.0
.venv/bin/python tests/upgrade_e2e.py --baseline v1.0.1
.venv/bin/python tests/upgrade_e2e.py --baseline v1.1.0
.venv/bin/python tests/readiness_load.py --seconds 15

python3 - "$root_dir" <<'PY'
import json
from pathlib import Path
import subprocess
import sys

out = Path(sys.argv[1]) / 'artifacts'
result = json.loads(Path('artifacts/e2e-results.json').read_text())
result['commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
result['results'].append({
    'id': 'CR-01',
    'status': 'PASS',
    'detail': (
        'Fresh local Git clone; uv.lock environment; npm ci and production build; '
        'floor guard against v1.4.0; Python, real-browser, frontend-state, '
        'zoom, three upgrade-baseline, and short load suites passed.'
    ),
})
result['results'].sort(key=lambda item: item['id'])
(out / 'clean-e2e-results.json').write_text(json.dumps(result, indent=2) + '\n')
(out / 'clean-corpus-results.json').write_bytes(Path('artifacts/corpus-results.json').read_bytes())
for name in [
    'adversarial-results.json',
    'interactions-results.json',
    'upgrade-results.json',
    'upgrade-v1.0.1-results.json',
    'upgrade-v1.1.0-results.json',
]:
    (out / ('clean-' + name)).write_bytes((Path('artifacts') / name).read_bytes())
print('Clean installation and acceptance suites passed at', result['commit'])
PY
