"""Launch actual application with destination-only network audit for offline E2E."""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def audit(event, args):
    if event == "socket.connect":
        with open(os.environ["CRW_NETWORK_AUDIT"], "a") as f:
            f.write(json.dumps({"destination": str(args[1])}) + "\n")
sys.addaudithook(audit)
import uvicorn
uvicorn.run("backend.workbench.main:app", host="127.0.0.1", port=int(os.environ["CRW_PORT"]), access_log=False, log_level="warning")
