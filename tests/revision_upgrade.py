"""Preserve actual v1.4.0 data through extraction-v6 reprocessing. Author: Ethan."""
from io import BytesIO
import json
import os
from pathlib import Path
import signal
import socket
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "03b6dbaed1fac5bc2cad833a20be0770d7bcf895"
RUN = Path(tempfile.mkdtemp(prefix="revision-upgrade-", dir=ROOT / "artifacts"))


def main():
    old = RUN / "v1.4.0"
    old.mkdir()
    with tarfile.open(fileobj=BytesIO(subprocess.check_output(["git", "archive", BASELINE], cwd=ROOT))) as archive:
        archive.extractall(old, filter="data")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    data = RUN / "data"
    network = RUN / "network.jsonl"
    network.touch()
    env = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"}
    env.update(CRW_DATA_DIR=str(data), CRW_PORT=str(port), CRW_NETWORK_AUDIT=str(network))
    server = None
    log = (RUN / "server.log").open("w")
    client = httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=30, trust_env=False)

    def stop():
        nonlocal server
        if server and server.poll() is None:
            os.killpg(server.pid, signal.SIGTERM)
            server.wait(timeout=10)
        server = None
        (RUN / "processes.json").write_text("[]")

    def start(root):
        nonlocal server
        stop()
        server = subprocess.Popen([sys.executable, "tests/serve_checked.py"], cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        (RUN / "processes.json").write_text(json.dumps([server.pid]))
        for _ in range(150):
            try:
                if client.get("/api/health").status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(.1)
        raise RuntimeError("Server failed to start")

    def raw_review(id):
        with sqlite3.connect(data / "workbench.sqlite3") as c:
            return c.execute("SELECT data FROM reviews WHERE id=?", (id,)).fetchone()[0]

    try:
        start(old)
        content = b"Each party's aggregate liability is capped at fees paid in the preceding 12 months.\nIndemnification obligations are excluded from the foregoing cap."
        doc = client.post("/api/documents", files={"file": ("baseline.txt", content)}).raise_for_status().json()
        review = client.post(f"/api/documents/{doc['id']}/reviews", json={"playbook_id": "commercial"}).raise_for_status().json()
        issue = next(i for i in review["issues"] if i["rule_id"] == "liability-cap")
        client.patch(f"/api/reviews/{review['id']}/issues/{issue['id']}", json={"status": "rejected", "notes": "Preserve this historical decision"}).raise_for_status()
        frozen = raw_review(review["id"])
        original = (data / "sources" / doc["id"]).read_bytes()
        start(ROOT)
        historical = client.get(f"/api/reviews/{review['id']}").raise_for_status().json()
        assert historical["verification_status"] == "HISTORICAL_UNVERIFIED"
        assert raw_review(review["id"]) == frozen
        assert client.post(f"/api/documents/{doc['id']}/reviews", json={"playbook_id": "commercial"}).status_code == 409
        reprocessed = client.post(f"/api/documents/{doc['id']}/reprocess").raise_for_status().json()
        current = client.post(f"/api/documents/{reprocessed['id']}/reviews", json={"playbook_id": "commercial"}).raise_for_status().json()
        assert current["verification_status"] == "CURRENT_CHECKS"
        assert all(i["status"] == "unresolved" and not i["notes"] for i in current["issues"])
        delta = client.get(f"/api/reviews/{current['id']}/comparison", params={"baseline_review_id": review["id"]}).raise_for_status().json()
        assert delta["same_original"] and delta["same_extracted_text"] and not delta["same_checks"]
        assert all(row["status"] == "NOT_COMPARABLE" for row in delta["rules"])
        assert any(row["revisit_prior_decisions"] for row in delta["rules"])
        assert any("no saved text digest" in warning for warning in delta["warnings"])
        assert raw_review(review["id"]) == frozen
        assert (data / "sources" / doc["id"]).read_bytes() == original == (data / "sources" / reprocessed["id"]).read_bytes()
        assert not network.read_text().strip()
        (RUN / "result.json").write_text(json.dumps({"author": "Ethan", "status": "PASS", "baseline": BASELINE,
            "checks": ["real released database and decisions preserved byte-for-byte", "old extraction blocked; reprocess creates a new record", "new review has fresh decisions", "comparison discloses different extraction rules and legacy digest gap", "original hashes unchanged; zero outbound connections"]}, indent=2))
        print(RUN)
    finally:
        stop()
        client.close()
        log.close()


if __name__ == "__main__":
    main()
