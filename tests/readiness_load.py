"""Bounded local HTTP load, large-history fixture, restart and diagnostics check."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid

import httpx

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--seconds", type=int, default=0, help="Additional sustained activity (0 to 600 seconds)")
args = parser.parse_args()
if not 0 <= args.seconds <= 600:
    parser.error("--seconds must be 0 through 600")

ROOT = Path(__file__).resolve().parents[1]
(ROOT / "artifacts/readiness").mkdir(parents=True, exist_ok=True)
RUN = Path(tempfile.mkdtemp(prefix="readiness-load-", dir=ROOT / "artifacts"))
(RUN / "network.jsonl").touch()
DATA = RUN / "data"
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0)); PORT = sock.getsockname()[1]
BASE = f"http://127.0.0.1:{PORT}"
environment = {**os.environ, "CRW_DATA_DIR": str(DATA), "CRW_PORT": str(PORT), "CRW_NETWORK_AUDIT": str(RUN / "network.jsonl")}
environment.pop("OPENROUTER_API_KEY", None)
log = (RUN / "server.log").open("w")
process = None

def stop():
    global process
    if process and process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=10)
    process = None

def start():
    global process
    process = subprocess.Popen([sys.executable, "tests/serve_checked.py"], cwd=ROOT, env=environment, stdout=log, stderr=log, start_new_session=True)
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            if client.get("/api/health").status_code == 200: return
        except httpx.HTTPError: pass
        time.sleep(.05)
    raise RuntimeError("Load server did not start")

try:
    with httpx.Client(base_url=BASE, timeout=30, trust_env=False) as client:
        start()
        doc = client.post("/api/documents", files={"file": ("synthetic-private-marker.txt", b"Each party aggregate liability will not exceed fees paid in the preceding twelve months.")}).raise_for_status().json()
        review = client.post(f"/api/documents/{doc['id']}/reviews", json={"playbook_id": "commercial"}).raise_for_status().json()
        stop()
        # Scale a real saved review into a labeled performance fixture, not a legal corpus.
        with sqlite3.connect(DATA / "workbench.sqlite3") as c:
            for _ in range(1000):
                replica = {**review, "id": str(uuid.uuid4())}
                c.execute("INSERT INTO reviews VALUES(?,?,?)", (replica["id"], doc["id"], json.dumps(replica)))
        start()
        rss_before = int(subprocess.check_output(["ps", "-o", "rss=", "-p", str(process.pid)], text=True).strip())
        durations = []
        def query(_):
            started = time.perf_counter()
            response = client.get(f"/api/documents/{doc['id']}/reviews?summary=true&limit=50")
            duration = time.perf_counter() - started
            response.raise_for_status()
            assert len(response.json()) == 50 and len(response.content) < 100_000
            assert all("issues" not in item for item in response.json())
            return duration
        with ThreadPoolExecutor(max_workers=8) as executor:
            durations = list(executor.map(query, range(240)))
            until = time.monotonic() + args.seconds
            while time.monotonic() < until:
                durations.extend(executor.map(query, range(80)))
                time.sleep(.2)
        rss_after = int(subprocess.check_output(["ps", "-o", "rss=", "-p", str(process.pid)], text=True).strip())
        # Actual parsing under a burst: either accepted or explicitly busy, never 500.
        def upload(_):
            return client.post("/api/documents", files={"file": ("burst.txt", b"Synthetic local load agreement.")}).status_code
        with ThreadPoolExecutor(max_workers=8) as executor:
            statuses = list(executor.map(upload, range(16)))
        assert set(statuses) <= {201, 503} and 201 in statuses
        assert client.get("/api/health").status_code == 200
        stop(); start()
        assert client.get(f"/api/documents/{doc['id']}/original").content.startswith(b"Each party")
        stop()
        records = [json.loads(line) for p in DATA.glob("diagnostics.jsonl*") for line in p.read_text().splitlines()]
        serialized = json.dumps(records)
        assert doc['id'] not in serialized and "synthetic-private-marker" not in serialized and "Each party" not in serialized
        assert any(r['status'] == 200 and r['route'] == '/api/documents/{id}/reviews' for r in records)
        assert (RUN / "network.jsonl").read_text() == ""
        durations.sort()
        result = {"author": "Ethan", "status": "PASS", "requests": len(durations), "concurrency": 8, "sustained_seconds": args.seconds, "rss_before_kib": rss_before, "rss_after_kib": rss_after, "history_rows": 1001,
                  "p50_ms": round(durations[int(len(durations)*.50)-1]*1000,2), "p95_ms": round(durations[int(len(durations)*.95)-1]*1000,2), "p99_ms": round(durations[int(len(durations)*.99)-1]*1000,2),
                  "upload_statuses": {str(s): statuses.count(s) for s in set(statuses)}, "run": str(RUN.relative_to(ROOT)),
                  "limits": "Bounded local workload; endpoint RSS samples do not establish absence of leaks. Not a long-duration reliability or legal accuracy benchmark."}
        (ROOT / ("artifacts/readiness/soak.json" if args.seconds else "artifacts/readiness/load.json")).write_text(json.dumps(result, indent=2)+"\n")
        print(json.dumps(result))
finally:
    stop(); log.close()
