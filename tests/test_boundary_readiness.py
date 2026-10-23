import asyncio
import json
import os
import subprocess
import sys

from fastapi.testclient import TestClient
import pytest

from backend.workbench import store
from backend.workbench.main import app


def test_validation_does_not_echo_private_input():
    client = TestClient(app, base_url="http://127.0.0.1")
    secret = "PRIVATE-CONTRACT-MARKER"
    response = client.post("/api/playbooks", json={"yaml": "name: " + secret})
    assert response.status_code == 422
    assert secret not in response.text
    response = client.post("/api/playbooks", json={"unexpected": secret})
    assert response.status_code == 422
    assert secret not in response.text


def test_diagnostics_are_bounded_and_content_free(tmp_path, monkeypatch):
    from backend.workbench.diagnostics import configure, event, close
    monkeypatch.setattr(store, "DATA", tmp_path)
    configure(tmp_path, max_bytes=512, backups=2)
    for _ in range(50):
        event("request", request_id="generated", entry_point="http", status=422, route="/api/playbooks", duration_ms=4)
    close()
    files = list(tmp_path.glob("diagnostics.jsonl*"))
    assert 1 <= len(files) <= 3
    for path in files:
        assert path.stat().st_size <= 512
        for line in path.read_text().splitlines():
            record = json.loads(line)
            assert set(record) == {"time", "event", "request_id", "entry_point", "status", "route", "duration_ms"}
            assert record["entry_point"] == "http"


def test_admission_rejects_excess_without_reading_body():
    from backend.workbench.diagnostics import LocalBoundary
    async def exercise():
        entered, release = asyncio.Event(), asyncio.Event()
        async def downstream(scope, receive, send):
            entered.set(); await release.wait()
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})
        boundary = LocalBoundary(downstream, max_active=1)
        async def receive():
            raise AssertionError("rejected request body must not be read")
        first, rejected = [], []
        async def send_first(message): first.append(message)
        async def send_rejected(message): rejected.append(message)
        scope = {"type": "http", "path": "/api/documents", "method": "POST", "headers": []}
        task = asyncio.create_task(boundary(scope.copy(), receive, send_first))
        await entered.wait()
        await boundary(scope.copy(), receive, send_rejected)
        assert rejected[0]["status"] == 503
        release.set(); await task
        assert boundary.active == 0
    asyncio.run(exercise())


def test_security_headers_cover_rejections():
    client = TestClient(app, base_url="http://127.0.0.1")
    response = client.post("/api/playbooks", headers={"Origin": "https://evil.example"}, json={})
    assert response.status_code == 403
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-request-id"]


@pytest.mark.parametrize("name,value", [("CRW_DATA_DIR", ""), ("CRW_RETENTION_DAYS", "-1"), ("CRW_RETENTION_DAYS", "abc")])
def test_invalid_storage_configuration_fails_explicitly(name, value):
    result = subprocess.run([sys.executable, "-c", "from backend.workbench import store"], env={**os.environ, name: value}, capture_output=True)
    assert result.returncode != 0
    assert name.encode() in result.stderr


def test_slow_request_body_has_total_read_deadline(monkeypatch):
    from fastapi import HTTPException
    from backend.workbench import main
    monkeypatch.setattr(main, "BODY_TIMEOUT_SECONDS", .02, raising=False)
    async def exercise():
        async def downstream(scope, receive, send):
            while True:
                message = await receive()
                if not message.get("more_body"):
                    break
        async def slow_receive():
            await asyncio.sleep(.015)
            return {"type": "http.request", "body": b"x", "more_body": True}
        async def send(message):
            raise AssertionError("incomplete upload must not succeed")
        with pytest.raises(HTTPException) as captured:
            await asyncio.wait_for(main.BodyLimit(downstream)({"type": "http", "path": "/api/documents", "headers": []}, slow_receive, send), .2)
        assert captured.value.status_code == 408
    asyncio.run(exercise())


def test_cancelled_request_releases_admission_capacity():
    from backend.workbench.diagnostics import LocalBoundary
    async def exercise():
        entered = asyncio.Event()
        async def downstream(scope, receive, send):
            entered.set()
            await asyncio.Event().wait()
        async def receive():
            return {"type": "http.request", "body": b""}
        async def send(message):
            pass
        boundary = LocalBoundary(downstream, max_active=1)
        task = asyncio.create_task(boundary({"type": "http", "method": "POST", "path": "/api/documents"}, receive, send))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert boundary.active == 0
        assert boundary.groups["upload"] == 0
    asyncio.run(exercise())


def test_fresh_store_starts_through_application_lifespan(tmp_path, monkeypatch):
    root = tmp_path / "brand-new-data"
    monkeypatch.setattr(store, "DATA", root)
    monkeypatch.setattr(store, "RETENTION_DAYS", 0)
    assert not root.exists()
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/documents").json() == []
    assert root.is_dir() and root.stat().st_mode & 0o077 == 0
