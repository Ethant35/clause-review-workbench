"""Stop only process groups registered by this project's E2E runner."""
import json
import os
from pathlib import Path
import signal
p = Path('artifacts/processes.json')
if p.exists():
    for pid in json.loads(p.read_text()):
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    print('Sent SIGTERM to registered project processes.')
