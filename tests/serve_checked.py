"""Launch actual application with destination-only network audit for offline E2E."""
import json
import os
from pathlib import Path
import sys
import asyncio
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def audit(event, args):
    if event == "socket.connect":
        with open(os.environ["CRW_NETWORK_AUDIT"], "a") as f:
            f.write(json.dumps({"destination": str(args[1])}) + "\n")
sys.addaudithook(audit)
import uvicorn
from backend.workbench.main import app

class DelayedRequest:
    """Hold a real local request when a frontend race test requests it."""
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        control_path = os.environ.get('CRW_DELAY_CONTROL')
        signal_path = os.environ.get('CRW_DELAY_SIGNAL')
        path = scope.get('path', '')
        if scope.get('type') == 'http' and control_path and signal_path and path.startswith('/api/'):
            control = Path(control_path)
            signal = Path(signal_path)
            while True:
                try:
                    state = json.loads(control.read_text())
                except (OSError, json.JSONDecodeError):
                    state = {}
                document_read = (scope.get('method') == 'GET' and path.startswith('/api/documents/')
                                 and path.count('/') == 3 and state.get('document_id') == path.rsplit('/', 1)[-1])
                if (document_read or state.get('path') == path) and state.get('hold'):
                    signal.write_text('entered')
                    await asyncio.sleep(.01)
                else:
                    if signal.exists():
                        signal.write_text('released')
                    break
        await self.inner(scope, receive, send)

app.add_middleware(DelayedRequest)
uvicorn.run(app, host="127.0.0.1", port=int(os.environ["CRW_PORT"]), access_log=False, log_level="warning")
