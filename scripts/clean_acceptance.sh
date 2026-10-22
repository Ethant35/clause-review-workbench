#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
root_dir="$PWD"
mkdir -p artifacts
clean_dir="$(mktemp -d "${TMPDIR:-/tmp}/crw-clean.XXXXXX")"
printf '%s\n' "$clean_dir" > artifacts/clean-checkout-path.txt
export CRW_PROCESS_REGISTRY="$root_dir/artifacts/processes.json"
git clone --no-local "$root_dir" "$clean_dir/repo"
cd "$clean_dir/repo"
uv sync --frozen --python 3.12
npm --prefix frontend ci
npm --prefix frontend run build
.venv/bin/python -m playwright install chromium
.venv/bin/python tests/e2e.py
.venv/bin/python tests/adversarial_e2e.py
.venv/bin/python tests/interactions_e2e.py
.venv/bin/python tests/upgrade_e2e.py
.venv/bin/python tests/upgrade_e2e.py --baseline v1.0.1
python3 - "$root_dir" <<'PY'
import json
from pathlib import Path
import subprocess
import sys
out=Path(sys.argv[1])/'artifacts'
result=json.loads(Path('artifacts/e2e-results.json').read_text())
result['commit']=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
result['results'].append({'id':'CR-01','status':'PASS','detail':'Fresh local Git clone; new Python environment installed from uv.lock; npm ci; production build; real server and Chromium E2E passed.'})
result['results'].sort(key=lambda x:x['id'])
(out/'clean-e2e-results.json').write_text(json.dumps(result,indent=2)+'\n')
(out/'clean-corpus-results.json').write_bytes(Path('artifacts/corpus-results.json').read_bytes())
for name in ['adversarial-results.json','interactions-results.json','upgrade-results.json','upgrade-v1.0.1-results.json']:
    (out/('clean-'+name)).write_bytes((Path('artifacts')/name).read_bytes())
print('Clean installation and E2E acceptance passed at',result['commit'])
PY
