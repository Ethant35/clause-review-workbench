"""PDF image intake and explicit, history-preserving reprocessing contracts."""
import hashlib
import json
import uuid
from pathlib import Path

import pytest
import pymupdf
from fastapi.testclient import TestClient

from backend.workbench import store
from backend.workbench.main import app, save_playbook
from backend.workbench.parsing import ParseError, extract
from backend.workbench.safety import EXTRACTION_REVISION


@pytest.fixture
def database(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA", tmp_path)
    monkeypatch.setattr(store, "RETENTION_DAYS", 0)
    store.initialize()
    return tmp_path


def pdf_with_image(*, page_text="Visible contract text.", image_text=None, fullpage=False):
    image_doc = pymupdf.open()
    image_page = image_doc.new_page(width=120, height=80)
    if image_text:
        image_page.insert_text((8, 30), image_text, fontsize=10)
    image_bytes = image_page.get_pixmap().tobytes("png")
    image_doc.close()
    output = pymupdf.open()
    page = output.new_page(width=612, height=792)
    page.insert_text((72, 72), page_text)
    rect = page.rect if fullpage else pymupdf.Rect(500, 20, 590, 80)
    page.insert_image(rect, stream=image_bytes, keep_proportion=not fullpage)
    result = output.tobytes()
    output.close()
    return result


def upload(client, data, name="agreement.pdf"):
    response = client.post("/api/documents", files={"file": (name, data, "application/pdf")})
    assert response.status_code == 201, response.text
    return response.json()


def test_text_pdf_with_logo_waits_for_human_visual_comparison(database):
    client = TestClient(app, base_url="http://127.0.0.1")
    doc = upload(client, pdf_with_image())
    assert doc["state"] == "needs_visual_check"
    assert doc["visual_check"]["status"] == "NEEDS_VISUAL_CHECK"
    assert len(doc["image_manifest"]) == 1
    image = doc["image_manifest"][0]
    assert image["page"] == 1 and len(image["bbox"]) == 4
    assert any("OCR" in warning and "Compare the original with all extracted text" in warning for warning in doc["warnings"])
    playbook_id = "commercial"
    assert client.post(f"/api/documents/{doc['id']}/reviews", json={"playbook_id": playbook_id}).status_code == 409
    blocked_ai = client.post(f"/api/reviews/missing/ai", json={"consent": True, "provider": "test", "model": "test-model"})
    assert blocked_ai.status_code == 404

    base = {"confirm_no_missing_text": True, "original_sha256": doc["sha256"],
            "extraction_revision": doc["extraction_revision"],
            "manifest_sha256": doc["visual_check"]["manifest_sha256"]}
    assert client.post(f"/api/documents/{doc['id']}/visual-check", json={**base, "confirm_no_missing_text": False}).status_code == 422
    assert client.post(f"/api/documents/{doc['id']}/visual-check", json={**base, "manifest_sha256": "0" * 64}).status_code == 409
    save_playbook(playbook_id, (Path(__file__).parents[1] / "playbooks/commercial.yaml").read_text())
    confirmed = client.post(f"/api/documents/{doc['id']}/visual-check", json=base)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["visual_check"]["status"] == "CONFIRMED"
    assert confirmed.json()["visual_check"]["confirmed_at"]
    review = client.post(f"/api/documents/{doc['id']}/reviews", json={"playbook_id": playbook_id})
    assert review.status_code == 201, review.text
    report = client.get(f"/api/reviews/{review.json()['id']}/export?format=json").json()
    assert report["source_visual_check"]["confirmed_manifest_sha256"] == base["manifest_sha256"]
    assert any("OCR was not performed" in warning for warning in report["source_warnings"])
    with store.db() as connection:
        changed = confirmed.json()
        changed["visual_check"]["status"] = "NEEDS_VISUAL_CHECK"
        connection.execute("UPDATE documents SET data=? WHERE id=?", (json.dumps(changed), doc["id"]))
    blocked_ai = client.post(f"/api/reviews/{review.json()['id']}/ai", json={"consent": True, "provider": "test", "model": "test-model"})
    assert blocked_ai.status_code == 409


@pytest.mark.parametrize("mixed", [False, True])
def test_scanned_or_mixed_textless_pages_remain_unsupported(database, mixed):
    doc = pymupdf.open()
    if mixed:
        page = doc.new_page()
        page.insert_text((72, 72), "First page terms.")
    page2 = doc.new_page()
    image_source = pymupdf.open()
    image_page = image_source.new_page(width=60, height=40)
    image_page.insert_text((5, 20), "Scanned terms", fontsize=9)
    image_bytes = image_page.get_pixmap().tobytes("png")
    image_source.close()
    page2.insert_image(page2.rect, stream=image_bytes, keep_proportion=False)
    data = doc.tobytes()
    doc.close()
    with pytest.raises(ParseError, match="pages without extractable text"):
        extract(data)


def test_page_scale_image_pdf_is_rejected_as_unverifiable_scan(database):
    with pytest.raises(ParseError, match="page-scale image"):
        extract(pdf_with_image(fullpage=True))


@pytest.mark.parametrize("filename", ["common-paper-mnda-1.0.pdf", "common-paper-design-partner-1.0.pdf"])
def test_public_commonpaper_banner_bleed_is_clipped_and_flagged(database, filename):
    path = Path(__file__).parents[1] / "corpus/public" / filename
    source = path.read_bytes()
    extracted = extract(source)
    assert extracted["visual_check"]["status"] == "NEEDS_VISUAL_CHECK"
    assert any(image["clipped"] for image in extracted["image_manifest"])
    assert all(0 <= value <= 1 for image in extracted["image_manifest"] for value in image["bbox"])
    assert any("extends beyond a page crop" in warning and "outside the crop is not analyzed" in warning for warning in extracted["warnings"])
    client = TestClient(app, base_url="http://127.0.0.1")
    document = upload(client, source, filename)
    assert document["visual_check"]["status"] == "NEEDS_VISUAL_CHECK"
    ack = {"confirm_no_missing_text": True, "original_sha256": document["sha256"],
           "extraction_revision": document["extraction_revision"],
           "manifest_sha256": document["visual_check"]["manifest_sha256"]}
    assert client.post(f"/api/documents/{document['id']}/visual-check", json=ack).status_code == 200
    save_playbook("commercial", (Path(__file__).parents[1] / "playbooks/commercial.yaml").read_text())
    reviewed = client.post(f"/api/documents/{document['id']}/reviews", json={"playbook_id": "commercial"})
    assert reviewed.status_code == 201, reviewed.text
    result = reviewed.json()
    anchored = [issue["source_anchor"] for issue in result["issues"] if issue.get("source_anchor")]
    assert anchored
    assert all(document["text"][anchor["start"]:anchor["end"]] == anchor["text"] for anchor in anchored)
    exported = client.get(f"/api/reviews/{result['id']}/export?format=json").json()
    assert exported["document"]["sha256"] == document["sha256"]
    assert any("extends beyond a page crop" in warning for warning in exported["source_warnings"])
    assert exported["source_visual_check"]["confirmed_manifest_sha256"] == ack["manifest_sha256"]


def test_rasterized_term_cannot_be_silently_reviewed(database):
    # This image contains an adverse term absent from the text layer. Extraction
    # cannot read it, so the service must wait for an explicit human comparison.
    doc = upload(TestClient(app, base_url="http://127.0.0.1"), pdf_with_image(image_text="Unlimited liability for all claims."))
    assert "Unlimited liability" not in doc["text"]
    assert doc["visual_check"]["status"] == "NEEDS_VISUAL_CHECK"


def test_reprocess_creates_fresh_lineage_without_copying_review_history(database):
    client = TestClient(app, base_url="http://127.0.0.1")
    source_bytes = b"A party may assign this agreement without consent."
    original = client.post("/api/documents", files={"file": ("terms.txt", source_bytes, "text/plain")}).json()
    save_playbook("commercial", (Path(__file__).parents[1] / "playbooks/commercial.yaml").read_text())
    first_review = client.post(f"/api/documents/{original['id']}/reviews", json={"playbook_id": "commercial"}).json()
    issue = first_review["issues"][0]
    client.patch(f"/api/reviews/{first_review['id']}/issues/{issue['id']}", json={"status": "accepted", "notes": "Keep historical note."})
    created = client.post(f"/api/documents/{original['id']}/reprocess")
    assert created.status_code == 201, created.text
    fresh = created.json()
    assert fresh["id"] != original["id"] and fresh["source_document_id"] == original["id"]
    assert fresh["sha256"] == hashlib.sha256(source_bytes).hexdigest()
    assert client.get(f"/api/documents/{fresh['id']}/reviews").json() == []
    history = client.get(f"/api/documents/{original['id']}/reviews").json()[0]
    assert history["issues"][0]["status"] == "accepted"
    assert history["issues"][0]["notes"] == "Keep historical note."
    assert (database / "sources" / original["id"]).read_bytes() == source_bytes
    listed = {item["id"] for item in client.get("/api/documents").json()}
    assert original["id"] in listed and fresh["id"] in listed


def test_reprocess_refuses_corrupt_or_deleted_original(database):
    client = TestClient(app, base_url="http://127.0.0.1")
    data = b"Source contract text."
    document = client.post("/api/documents", files={"file": ("source.txt", data, "text/plain")}).json()
    (database / "sources" / document["id"]).write_bytes(b"tampered")
    assert client.post(f"/api/documents/{document['id']}/reprocess").status_code == 409
    assert client.delete(f"/api/documents/{document['id']}").status_code == 200
    assert client.post(f"/api/documents/{document['id']}/reprocess").status_code == 404


def test_source_linked_review_original_and_exports_reject_tampered_bytes(database):
    client = TestClient(app, base_url="http://127.0.0.1")
    data = b"A party may assign this agreement without consent."
    document = client.post("/api/documents", files={"file": ("source.txt", data, "text/plain")}).json()
    save_playbook("commercial", (Path(__file__).parents[1] / "playbooks/commercial.yaml").read_text())
    review = client.post(f"/api/documents/{document['id']}/reviews", json={"playbook_id": "commercial"}).json()
    (database / "sources" / document["id"]).write_bytes(b"different source")
    assert client.post(f"/api/documents/{document['id']}/reviews", json={"playbook_id": "commercial"}).status_code == 409
    assert client.get(f"/api/documents/{document['id']}/original").status_code == 409
    assert client.get(f"/api/reviews/{review['id']}/export?format=json").status_code == 409
    assert client.post(f"/api/reviews/{review['id']}/ai", json={"consent": True, "provider": "test", "model": "test-model"}).status_code == 409


def test_reprocess_detects_parent_deletion_during_parse(database, monkeypatch):
    client = TestClient(app, base_url="http://127.0.0.1")
    data = b"Source contract text."
    document = client.post("/api/documents", files={"file": ("source.txt", data, "text/plain")}).json()
    from backend.workbench import main
    real_parse = main.parse_bytes

    def delete_parent_while_parsing(contents):
        parsed = real_parse(contents)
        store.delete_document(document["id"])
        return parsed

    monkeypatch.setattr(main, "parse_bytes", delete_parent_while_parsing)
    response = client.post(f"/api/documents/{document['id']}/reprocess")
    assert response.status_code == 409
    assert client.get("/api/documents").json() == []
    assert list((database / "sources").iterdir()) == []


def test_reprocess_failed_database_publish_cleans_new_source(database, monkeypatch):
    client = TestClient(app, base_url="http://127.0.0.1", raise_server_exceptions=False)
    data = b"Source contract text."
    document = client.post("/api/documents", files={"file": ("source.txt", data, "text/plain")}).json()
    new_id = str(uuid.uuid4())
    with store.db() as connection:
        connection.execute(
            "CREATE TRIGGER fail_reprocess BEFORE INSERT ON documents "
            f"WHEN new.id='{new_id}' BEGIN SELECT RAISE(ABORT, 'controlled insert failure'); END"
        )
    from backend.workbench import usability_intake
    monkeypatch.setattr(usability_intake, "uuid", type("UUIDFactory", (), {"uuid4": staticmethod(lambda: uuid.UUID(new_id))}))
    response = client.post(f"/api/documents/{document['id']}/reprocess")
    assert response.status_code == 503
    assert not (database / "sources" / new_id).exists()
    with store.db() as connection:
        assert connection.execute("SELECT 1 FROM pending_uploads WHERE id=?", (new_id,)).fetchone() is None


def test_unknown_database_publish_preserves_source_for_startup_resolution(database, monkeypatch):
    client = TestClient(app, base_url="http://127.0.0.1", raise_server_exceptions=False)
    data = b"Source contract text."
    document = client.post("/api/documents", files={"file": ("source.txt", data, "text/plain")}).json()
    new_id = str(uuid.uuid4())
    with store.db() as connection:
        connection.execute(
            "CREATE TRIGGER fail_reprocess BEFORE INSERT ON documents "
            f"WHEN new.id='{new_id}' BEGIN SELECT RAISE(ABORT, 'controlled insert failure'); END"
        )
    from backend.workbench import usability_intake
    monkeypatch.setattr(usability_intake, "uuid", type("UUIDFactory", (), {"uuid4": staticmethod(lambda: uuid.UUID(new_id))}))
    get = store.get

    def unknown_publish_state(table, item):
        if table == "documents" and item == new_id:
            raise OSError("controlled database status failure")
        return get(table, item)

    monkeypatch.setattr(store, "get", unknown_publish_state)
    response = client.post(f"/api/documents/{document['id']}/reprocess")
    assert response.status_code == 503
    assert (database / "sources" / new_id).read_bytes() == data
    with store.db() as connection:
        assert connection.execute("SELECT 1 FROM pending_uploads WHERE id=?", (new_id,)).fetchone()
    monkeypatch.setattr(store, "get", get)
    store.initialize()
    assert not (database / "sources" / new_id).exists()


def test_retention_delete_retry_does_not_remove_an_active_reprocess_source(database, monkeypatch):
    client = TestClient(app, base_url="http://127.0.0.1")
    data = b"Source contract text."
    document = client.post("/api/documents", files={"file": ("source.txt", data, "text/plain")}).json()
    new_id = str(uuid.uuid4())
    from backend.workbench import usability_intake
    monkeypatch.setattr(usability_intake, "uuid", type("UUIDFactory", (), {"uuid4": staticmethod(lambda: uuid.UUID(new_id))}))
    real_open = usability_intake.os.open

    def open_then_run_retention(path, *args, **kwargs):
        fd = real_open(path, *args, **kwargs)
        if Path(path).name == new_id:
            # The periodic deletion retry runs while the request is active.
            store.retry_deletions()
        return fd

    monkeypatch.setattr(usability_intake.os, "open", open_then_run_retention)
    response = client.post(f"/api/documents/{document['id']}/reprocess")
    assert response.status_code == 201, response.text
    assert response.json()["id"] == new_id
    assert (database / "sources" / new_id).read_bytes() == data
    with store.db() as connection:
        assert connection.execute("SELECT 1 FROM pending_uploads WHERE id=?", (new_id,)).fetchone() is None


def test_startup_cleans_abandoned_unpublished_source(database):
    pending = str(uuid.uuid4())
    source = database / "sources" / pending
    source.write_bytes(b"interrupted reprocess")
    with store.db() as connection:
        connection.execute("INSERT INTO pending_uploads VALUES(?)", (pending,))
    store.initialize()
    assert not source.exists()
    with store.db() as connection:
        assert connection.execute("SELECT 1 FROM pending_uploads WHERE id=?", (pending,)).fetchone() is None
