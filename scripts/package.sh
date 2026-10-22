#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
npm --prefix frontend ci
npm --prefix frontend run build
mkdir -p artifacts
python3 - <<'PY'
from pathlib import Path
import subprocess
import tarfile
root=Path.cwd()
files=[Path(x) for x in subprocess.check_output(['git','ls-files'],text=True).splitlines()]
files+=list(Path('frontend/dist').rglob('*'))
name='clause-review-workbench-1.0.0'
with tarfile.open('artifacts/'+name+'.tar.gz','w:gz') as tar:
    for p in sorted(set(files)):
        if p.is_file() and not str(p).startswith('evidence/'):
            info=tar.gettarinfo(str(p),arcname=name+'/'+str(p))
            info.uid=info.gid=0;info.uname=info.gname='Ethan';info.mtime=0
            with p.open('rb') as f:tar.addfile(info,f)
print('artifacts/'+name+'.tar.gz')
PY
