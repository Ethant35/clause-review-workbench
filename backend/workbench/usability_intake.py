"""Explicit raster-image checks and lineage-preserving original reprocessing."""
import hashlib
import json
import os
import time
import uuid

from fastapi import APIRouter, HTTPException

from . import store
from .models import VisualCheckInput
from .safety import EXTRACTION_REVISION, visual_check_current

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _source_bytes(document):
    try:
        data = store.source_path(document["id"]).read_bytes()
    except (OSError, ValueError) as exc:
        raise HTTPException(409, "The stored original is unavailable. The document was not reprocessed.") from exc
    if hashlib.sha256(data).hexdigest() != document.get("sha256"):
        raise HTTPException(409, "The stored original failed its SHA256 check. The document was not reprocessed.")
    return data


@router.post("/{id}/visual-check")
def confirm_visual_check(id: str, body: VisualCheckInput):
    with store.db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT data FROM documents WHERE id=?", (id,)).fetchone()
        if not row:
            raise HTTPException(404, "Document not found")
        document = json.loads(row[0])
        current = document.get("visual_check") or {}
        if current.get("status") != "NEEDS_VISUAL_CHECK":
            raise HTTPException(409, "This document has no pending raster image check.")
        if (body.original_sha256 != document.get("sha256") or
                body.extraction_revision != EXTRACTION_REVISION or
                document.get("extraction_revision") != EXTRACTION_REVISION or
                body.manifest_sha256 != current.get("manifest_sha256")):
            raise HTTPException(409, "The source, image manifest, or extraction revision changed. Refresh the document before confirming.")
        # Verify the durable source while holding the write transaction so a
        # concurrent delete cannot make a stale acknowledgement effective.
        _source_bytes(document)
        stamp = {"status": "CONFIRMED", "original_sha256": document["sha256"],
                 "extraction_revision": EXTRACTION_REVISION,
                 "manifest_sha256": current["manifest_sha256"],
                 "confirmed_manifest_sha256": current["manifest_sha256"],
                 "confirmed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        document["visual_check"] = stamp
        document["state"] = "ready"
        connection.execute("UPDATE documents SET data=? WHERE id=?", (json.dumps(document), id))
    return document


@router.post("/{id}/reprocess", status_code=201)
def reprocess(id: str):
    original = store.get("documents", id)
    if original is None:
        raise HTTPException(404, "Document not found")
    data = _source_bytes(original)
    try:
        # Lazy import avoids coupling the router module to FastAPI app setup.
        from .main import parse_bytes
        parsed = parse_bytes(data)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, "The stored original cannot be reprocessed safely.") from exc
    new_id = str(uuid.uuid4())
    obj = dict(id=new_id, source_document_id=id, name=original.get("name", "document"),
               format=parsed.pop("format"), created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               state="needs_visual_check" if parsed.get("visual_check", {}).get("status") == "NEEDS_VISUAL_CHECK" else "ready",
               sha256=hashlib.sha256(data).hexdigest(), **parsed)
    target = store.source_path(new_id)
    if target.exists():
        raise HTTPException(503, "Could not allocate a new source record. Retry the reprocess request.")
    try:
        # Persist a startup-only staging marker before creating bytes. The
        # retention loop never consumes this table while the request is active.
        with store.db() as connection:
            connection.execute("BEGIN IMMEDIATE")
            parent = connection.execute("SELECT data FROM documents WHERE id=?", (id,)).fetchone()
            if not parent:
                raise HTTPException(409, "The source document was deleted during reprocessing.")
            parent_obj = json.loads(parent[0])
            try:
                checked_data = store.source_path(id).read_bytes()
            except (OSError, ValueError) as exc:
                raise HTTPException(409, "The stored original became unavailable during reprocessing.") from exc
            if hashlib.sha256(checked_data).hexdigest() != parent_obj.get("sha256") or checked_data != data:
                raise HTTPException(409, "The stored original changed during reprocessing.")
            connection.execute("INSERT INTO pending_uploads VALUES(?)", (new_id,))
        # Same-filesystem exclusive creation avoids overwriting an existing
        # source if a UUID collision or unexpected file is present.
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as source:
            source.write(data)
            source.flush()
            os.fsync(source.fileno())
        with store.db() as connection:
            connection.execute("BEGIN IMMEDIATE")
            parent = connection.execute("SELECT data FROM documents WHERE id=?", (id,)).fetchone()
            if not parent:
                raise HTTPException(409, "The source document was deleted during reprocessing.")
            parent_obj = json.loads(parent[0])
            try:
                checked_data = store.source_path(id).read_bytes()
            except (OSError, ValueError) as exc:
                raise HTTPException(409, "The stored original became unavailable during reprocessing.") from exc
            if hashlib.sha256(checked_data).hexdigest() != parent_obj.get("sha256") or checked_data != data:
                raise HTTPException(409, "The stored original changed during reprocessing.")
            # Publish the row and clear the durable cleanup marker atomically.
            # Every response after this point corresponds to a complete copy.
            connection.execute("INSERT INTO documents VALUES(?,?,?)", (new_id, time.time(), json.dumps(obj)))
            connection.execute("DELETE FROM pending_uploads WHERE id=?", (new_id,))
    except Exception:
        # A commit error can be reported after SQLite has committed. Preserve a
        # published row; otherwise remove bytes and clear the marker only after
        # the unlink succeeds. A failed unlink stays queued for startup cleanup.
        status_known = True
        try:
            published = store.get("documents", new_id)
        except Exception:
            published = None
            status_known = False
        if status_known and published is not None:
            try:
                with store.db() as connection:
                    connection.execute("DELETE FROM pending_uploads WHERE id=?", (new_id,))
            except Exception:
                pass
        elif status_known:
            try:
                target.unlink(missing_ok=True)
            except OSError:
                pass
            else:
                try:
                    with store.db() as connection:
                        connection.execute("DELETE FROM pending_uploads WHERE id=?", (new_id,))
                except Exception:
                    pass
        raise
    return obj
