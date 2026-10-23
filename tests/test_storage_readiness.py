"""Real SQLite/API regressions; faults are injected at the filesystem boundary."""
import json
import sqlite3
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.workbench import store
from backend.workbench.main import app
from backend.workbench.safety import EXTRACTION_REVISION, REVIEW_REVISION


@pytest.fixture
def database(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA", tmp_path)
    monkeypatch.setattr(store, "RETENTION_DAYS", 0)
    store.initialize()
    return tmp_path


def seed():
    document_id, review_id = str(uuid.uuid4()), str(uuid.uuid4())
    doc = {"id": document_id, "name": "example.txt", "text": "private text", "blocks": [], "warnings": []}
    rev = {"id": review_id, "document_id": document_id, "created_at": "2026-01-01", "playbook_id": "test", "playbook_name": "Test", "ai_status": "NOT_REQUESTED", "review_revision": REVIEW_REVISION, "extraction_revision": EXTRACTION_REVISION, "issues": [{"id": "issue", "rule_id": "test", "status": "unresolved", "notes": "keep this note"}], "checks": [], "playbook_snapshot": {"rules": []}}
    with store.db() as connection:
        connection.execute("INSERT INTO documents VALUES(?,?,?)", (document_id, 1, json.dumps(doc)))
        connection.execute("INSERT INTO reviews VALUES(?,?,?)", (review_id, document_id, json.dumps(rev)))
    (store.DATA / "sources" / document_id).write_bytes(b"original bytes")
    return document_id, review_id


def test_connection_closed_after_transaction(database):
    with store.db() as connection:
        connection.execute("SELECT 1")
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connection.execute("SELECT 1")


def test_delete_rollback_preserves_original_and_review(database):
    document_id, review_id = seed()
    with store.db() as connection:
        connection.execute("CREATE TRIGGER block_delete BEFORE DELETE ON documents BEGIN SELECT RAISE(ABORT, 'controlled disk failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        store.delete_document(document_id)
    assert (database / "sources" / document_id).read_bytes() == b"original bytes"
    assert store.get("reviews", review_id) is not None


def test_delete_unlink_failure_is_retryable_after_restart(database, monkeypatch):
    document_id, review_id = seed()
    unlink = Path.unlink
    def fail_source(path, *args, **kwargs):
        if path.name == document_id:
            raise PermissionError("controlled filesystem failure")
        return unlink(path, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", fail_source)
        with pytest.raises(OSError):
            store.delete_document(document_id)
    store.initialize()
    assert not (database / "sources" / document_id).exists()
    assert store.get("documents", document_id) is None
    assert store.get("reviews", review_id) is None


def test_status_patch_preserves_note_and_note_patch_preserves_status(database):
    _, review_id = seed()
    client = TestClient(app, base_url="http://127.0.0.1")
    url = f"/api/reviews/{review_id}/issues/issue"
    response = client.patch(url, json={"status": "accepted"})
    assert response.status_code == 200
    assert response.json()["notes"] == "keep this note"
    response = client.patch(url, json={"notes": "new note"})
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    for body in ({}, {"status": None}, {"notes": None}):
        assert client.patch(url, json=body).status_code == 422


def test_lists_are_bounded_and_summaries_omit_payloads(database):
    document_id, _ = seed()
    seed()
    client = TestClient(app, base_url="http://127.0.0.1")
    page = client.get("/api/documents?limit=1&offset=0").json()
    assert len(page) == 1
    assert not {"text", "blocks", "warnings"}.intersection(page[0])
    assert client.get("/api/documents?limit=101").status_code == 422
    assert client.get("/api/documents?offset=-1").status_code == 422
    summary = client.get(f"/api/documents/{document_id}/reviews?summary=true").json()[0]
    assert summary["verification_status"] == "CURRENT_CHECKS"
    assert not {"issues", "checks", "playbook_snapshot"}.intersection(summary)


def test_concurrent_edits_preserve_both_fields(database):
    _, review_id = seed()
    client = TestClient(app, base_url="http://127.0.0.1")
    url = f"/api/reviews/{review_id}/issues/issue"
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(client.patch, url, json=patch) for patch in ({"status": "accepted"}, {"notes": "concurrent note"})]
        assert all(f.result().status_code == 200 for f in futures)
    issue = store.get("reviews", review_id)["issues"][0]
    assert (issue["status"], issue["notes"]) == ("accepted", "concurrent note")


def test_sqlite_full_rollback_keeps_prior_rows(database):
    document_id, _ = seed()
    with pytest.raises(sqlite3.OperationalError, match="full"):
        with store.db() as c:
            pages = c.execute("PRAGMA page_count").fetchone()[0]
            c.execute(f"PRAGMA max_page_count={pages}")
            c.execute("INSERT INTO playbooks VALUES('large', ?)", ("x" * 1_000_000,))
    assert store.get("documents", document_id) is not None
    assert store.get("playbooks", "large") is None
    assert (database / "sources" / document_id).read_bytes() == b"original bytes"


def test_partial_source_write_failure_removes_uncommitted_bytes(database, monkeypatch):
    original = Path.write_bytes
    def full_disk(path, data):
        if path.parent == database / "sources":
            original(path, data[:5])
            raise OSError("controlled disk full while writing source")
        return original(path, data)
    monkeypatch.setattr(Path, "write_bytes", full_disk)
    client = TestClient(app, base_url="http://127.0.0.1")
    response = client.post("/api/documents", files={"file": ("synthetic.txt", b"Synthetic contract text.")})
    assert response.status_code == 503
    assert list((database / "sources").iterdir()) == []
    assert client.get("/api/documents").json() == []
