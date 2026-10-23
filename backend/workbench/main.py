import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
import sqlite3
from pathlib import Path
import subprocess
import sys
import time
import uuid

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware
import yaml
from pydantic import ValidationError
from . import store
from .models import Playbook, YAMLInput, ReviewInput, Decision, AIInput
from .relations import InteractionLimit
from .engine import analyze
from .reports import export
from .ai import assist, AIError
from .safety import EXTRACTION_REVISION, REVIEW_REVISION, review_view, visual_check_current
from .usability_intake import router as usability_intake_router
from .playbook_settings import router as playbook_settings_router
from .recovery import exclusive_store
from . import diagnostics

ROOT = Path(__file__).resolve().parents[2]
MAX_UPLOAD = 10 * 1024 * 1024
BODY_TIMEOUT_SECONDS = 30
PROCESSING = asyncio.Semaphore(2)
AI_LOCK = asyncio.Lock()

class UniqueLoader(yaml.SafeLoader):
    pass

def mapping(loader, node, deep=False):
    result = {}
    for key, value in node.value:
        k = loader.construct_object(key, deep=deep)
        if not isinstance(k, str) or k in result:
            raise ValueError("YAML keys must be unique strings")
        result[k] = loader.construct_object(value, deep=deep)
    return result
UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)

def parse_playbook(text):
    try:
        # Alias expansion/cycles are unnecessary for a simple auditable playbook.
        if any(isinstance(t, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken)) for t in yaml.scan(text)):
            raise ValueError("YAML anchors and aliases are unsupported")
        return Playbook.model_validate(yaml.load(text, Loader=UniqueLoader))
    except (yaml.YAMLError, ValidationError, ValueError, RecursionError) as exc:
        raise HTTPException(422, "Invalid playbook. Check required fields, unique rule IDs, patterns, and YAML structure; aliases are unsupported.") from exc

def save_playbook(id, text):
    pb = parse_playbook(text)
    obj = {"id": id, "name": pb.name, "version": pb.version, "description": pb.description, "yaml": text}
    with store.db() as c:
        c.execute("INSERT INTO playbooks(id,data) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data", (id, json.dumps(obj)))
    return obj

async def retention_loop():
    while True:
        await asyncio.sleep(60)
        try:
            await run_in_threadpool(store.purge_expired)
        except (OSError, ValueError, sqlite3.Error):
            diagnostics.event("retention_failed", request_id=str(uuid.uuid4()), entry_point="retention", status=503, route="retention", duration_ms=0)

@asynccontextmanager
async def lifespan(app):
    store.DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
    with exclusive_store(store.DATA):
        store.initialize()
        diagnostics.configure(store.DATA)
        for path in (ROOT / "playbooks").glob("*.yaml"):
            if not store.get("playbooks", path.stem):
                save_playbook(path.stem, path.read_text())
        task = asyncio.create_task(retention_loop())
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            diagnostics.close()

app = FastAPI(title="Clause Review Workbench", version="1.3.0", lifespan=lifespan, docs_url=None, redoc_url=None)
app.include_router(usability_intake_router)
app.include_router(playbook_settings_router)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])

@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    return JSONResponse({"detail": "Invalid request fields or values. Check the API contract."}, 422)

@app.middleware("http")
async def local_security(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        allowed = {"http://127.0.0.1:5173", "http://localhost:5173", str(request.base_url).rstrip("/")}
        if origin and origin not in allowed:
            return JSONResponse({"detail": "Cross-origin write rejected"}, status_code=403)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"detail": "Cross-site request rejected"}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'"
    return response

class BodyLimit:
    def __init__(self, app): self.app = app
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            declared = MAX_UPLOAD + 2_000_000
        limit = MAX_UPLOAD + 1_000_000 if scope.get("path") == "/api/documents" else 300_000
        if declared > limit:
            return await JSONResponse({"detail": "Request exceeds size limit"}, 413)(scope, receive, send)
        count = 0
        deadline = time.monotonic() + BODY_TIMEOUT_SECONDS
        async def bounded():
            nonlocal count
            try:
                async with asyncio.timeout(max(0, deadline - time.monotonic())):
                    message = await receive()
            except TimeoutError as exc:
                raise HTTPException(408, "Request body exceeded the 30-second read limit") from exc
            count += len(message.get("body", b""))
            if count > limit:
                raise HTTPException(413, "Request exceeds size limit")
            return message
        await self.app(scope, bounded, send)
app.add_middleware(BodyLimit)
app.add_middleware(diagnostics.LocalBoundary)

def require(table, id):
    obj = store.get(table, id)
    if obj is None:
        raise HTTPException(404, "Record not found")
    return review_view(obj) if table == "reviews" else obj

def now(): return datetime.now(timezone.utc).isoformat()

def verify_document_original(doc):
    """Check the durable source before producing source-linked results."""
    try:
        original = store.source_path(doc["id"]).read_bytes()
    except (OSError, ValueError, KeyError) as exc:
        raise HTTPException(409, "The stored original is unavailable or unsafe. No source-linked result was created.") from exc
    if not doc.get("sha256") or hashlib.sha256(original).hexdigest() != doc["sha256"]:
        raise HTTPException(409, "The stored original failed its SHA256 check. No source-linked result was created.")

def update_ai(id, fields, issues=None):
    with store.db() as c:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT data FROM reviews WHERE id=?", (id,)).fetchone()
        if not row: raise HTTPException(404, "Review no longer exists")
        review = json.loads(row[0])
        review.update(fields)
        if issues: review["issues"].extend(issues)
        c.execute("UPDATE reviews SET data=? WHERE id=?", (json.dumps(review), id))
        return review_view(review)

@app.get("/api/health")
def health():
    return {"status": "ok", "ai_configured": bool(os.environ.get("OPENROUTER_API_KEY")), "retention_days": store.RETENTION_DAYS, "max_upload_bytes": MAX_UPLOAD, "extraction_revision": EXTRACTION_REVISION, "review_revision": REVIEW_REVISION}

@app.get("/api/documents")
def documents(limit: int = Query(100, ge=1, le=100), offset: int = Query(0, ge=0)):
    with store.db() as c:
        return [json.loads(r[0]) for r in c.execute("SELECT json_remove(data, '$.text', '$.blocks', '$.warnings') FROM documents ORDER BY created DESC, id DESC LIMIT ? OFFSET ?", (limit, offset))]

def parse_bytes(data):
    try:
        p = subprocess.run([sys.executable, "-m", "backend.workbench.parser_worker"], input=data, capture_output=True, timeout=15, cwd=ROOT)
        if p.returncode:
            raise HTTPException(422, "Document processing exceeded limits or failed safely")
        result = json.loads(p.stdout)
        if "error" in result:
            raise HTTPException(422, result["error"])
        return result["result"]
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        raise HTTPException(422, "Document processing exceeded limits") from exc

@app.post("/api/documents", status_code=201)
async def upload(file: UploadFile = File(...)):
    data = await file.read(MAX_UPLOAD + 1)
    await file.close()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "File exceeds the 10 MiB upload limit")
    async with PROCESSING:
        parsed = await run_in_threadpool(parse_bytes, data)
    id = str(uuid.uuid4())
    # Display-only sanitized filename; disk storage never uses an uploaded name.
    name = (file.filename or "document").replace("\\", "/").split("/")[-1]
    name = "".join(c for c in name if c.isprintable())[:200] or "document"
    visual_check = parsed.get("visual_check", {})
    obj = dict(id=id, name=name, format=parsed.pop("format"), created_at=now(), state="needs_visual_check" if visual_check.get("status") == "NEEDS_VISUAL_CHECK" else "ready", sha256=hashlib.sha256(data).hexdigest(), **parsed)
    path = store.DATA / "sources" / id
    try:
        path.write_bytes(data)
        path.chmod(0o600)
        with store.db() as c:
            c.execute("INSERT INTO documents VALUES(?,?,?)", (id, time.time(), json.dumps(obj)))
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return obj

@app.get("/api/documents/{id}")
def document(id: str): return require("documents", id)

@app.get("/api/documents/{id}/original")
def original(id: str):
    doc = require("documents", id)
    verify_document_original(doc)
    mime = {"pdf":"application/pdf", "txt":"text/plain", "docx":"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}[doc["format"]]
    return FileResponse(store.source_path(doc["id"]), media_type=mime, filename=doc["name"], content_disposition_type="inline" if doc["format"] == "pdf" else "attachment")

@app.delete("/api/documents/{id}")
def delete(id: str):
    try:
        deleted = store.delete_document(id)
    except ValueError as exc:
        raise HTTPException(404, "Record not found") from exc
    except OSError as exc:
        raise HTTPException(503, "Deletion is pending. Check storage permissions and retry; cleanup also resumes on restart.") from exc
    if not deleted:
        raise HTTPException(404, "Record not found")
    return {"deleted": True}

@app.get("/api/playbooks")
def playbooks():
    with store.db() as c:
        return [{k:v for k,v in json.loads(r[0]).items() if k != "yaml"} for r in c.execute("SELECT data FROM playbooks ORDER BY id")]

@app.get("/api/playbooks/{id}")
def playbook(id: str): return require("playbooks", id)

@app.post("/api/playbooks", status_code=201)
def new_playbook(body: YAMLInput): return save_playbook(str(uuid.uuid4()), body.yaml)

@app.put("/api/playbooks/{id}")
def update_playbook(id: str, body: YAMLInput):
    require("playbooks", id)
    return save_playbook(id, body.yaml)

@app.post("/api/playbooks/{id}/duplicate", status_code=201)
def duplicate_playbook(id: str):
    pb = parse_playbook(require("playbooks", id)["yaml"]).model_dump()
    pb["name"] = pb["name"][:110] + " copy"
    return save_playbook(str(uuid.uuid4()), yaml.safe_dump(pb, sort_keys=False))

@app.get("/api/playbooks/{id}/export")
def export_playbook(id: str):
    return Response(require("playbooks", id)["yaml"], media_type="application/yaml", headers={"Content-Disposition": 'attachment; filename="playbook.yaml"'})

@app.get("/api/documents/{id}/reviews")
def reviews(id: str, summary: bool = False, limit: int = Query(100, ge=1, le=100), offset: int = Query(0, ge=0)):
    require("documents", id)
    projection = "json_remove(data, '$.issues', '$.checks', '$.playbook_snapshot', '$.ai_audit', '$.ai_error')" if summary else "data"
    with store.db() as c:
        rows = [json.loads(r[0]) for r in c.execute(f"SELECT {projection} FROM reviews WHERE document_id=? ORDER BY rowid DESC LIMIT ? OFFSET ?", (id, limit, offset))]
    if not summary:
        return [review_view(row) for row in rows]
    return [{k: v for k, v in review_view({**row, "issues": []}).items() if k != "issues"} for row in rows]

@app.post("/api/documents/{id}/reviews", status_code=201)
def run_review(id: str, body: ReviewInput):
    doc = require("documents", id)
    verify_document_original(doc)
    if doc.get("extraction_revision") != EXTRACTION_REVISION:
        raise HTTPException(409, "This upload predates the current extraction checks. Download and re-upload the original before reviewing.")
    if not visual_check_current(doc):
        raise HTTPException(409, "Compare every raster image in the original with the extracted text, then confirm the visual check before reviewing.")
    pb = parse_playbook(require("playbooks", body.playbook_id)["yaml"])
    try:
        issues, checks = analyze(doc, pb)
    except InteractionLimit as exc:
        raise HTTPException(422, str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(422, "Playbook pattern exceeded its processing time limit") from exc
    review = dict(id=str(uuid.uuid4()), review_revision=REVIEW_REVISION, extraction_revision=EXTRACTION_REVISION, document_id=id, playbook_id=body.playbook_id, playbook_name=pb.name, created_at=now(), issues=issues, checks=checks, ai_status="NOT_REQUESTED", ai_error=None, playbook_snapshot=pb.model_dump(), source_warnings=list(doc.get("warnings") or []), source_visual_check=dict(doc.get("visual_check") or {}))
    with store.db() as c:
        c.execute("INSERT INTO reviews VALUES(?,?,?)", (review["id"], id, json.dumps(review)))
    return review_view(review)

@app.get("/api/reviews/{id}")
def review(id: str): return require("reviews", id)

@app.patch("/api/reviews/{id}/issues/{issue_id}")
def decision(id: str, issue_id: str, body: Decision):
    # Atomic read-modify-write prevents lost edits between browser tabs.
    with store.db() as c:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT data FROM reviews WHERE id=?", (id,)).fetchone()
        if not row: raise HTTPException(404, "Review not found")
        rev = json.loads(row[0])
        issue = next((i for i in rev["issues"] if i["id"] == issue_id), None)
        if not issue: raise HTTPException(404, "Issue not found")
        issue.update(body.model_dump(exclude_unset=True))
        c.execute("UPDATE reviews SET data=? WHERE id=?", (json.dumps(rev), id))
    return next(i for i in review_view(rev)["issues"] if i["id"] == issue_id)

@app.get("/api/reviews/{id}/export")
def report(id: str, format: str = "json"):
    if format not in {"json", "markdown", "docx"}: raise HTTPException(422, "Unknown export format")
    rev = require("reviews", id)
    doc = require("documents", rev["document_id"])
    verify_document_original(doc)
    data, mime, ext = export(rev, doc, format)
    return Response(data, media_type=mime, headers={"Content-Disposition": f'attachment; filename="review-{id}.{ext}"'})

@app.post("/api/reviews/{id}/ai")
async def ai_review(id: str, body: AIInput):
    if not body.consent: raise HTTPException(403, "Explicit external transmission consent is required")
    async with AI_LOCK:
        rev = require("reviews", id)
        doc = require("documents", rev["document_id"])
        verify_document_original(doc)
        if doc.get("extraction_revision") != EXTRACTION_REVISION or rev.get("review_revision") != REVIEW_REVISION:
            raise HTTPException(409, "Historical extraction/review is unverified. Re-upload the original and run a new review before AI assistance.")
        if not visual_check_current(doc):
            raise HTTPException(409, "Compare every raster image in the original with the extracted text, then confirm the visual check before AI assistance.")
        attempt = {**body.model_dump(), "attempt_id": str(uuid.uuid4()), "started_at": now()}
        update_ai(id, {"ai_status": "IN_PROGRESS", "ai_error": None, "ai_audit": attempt})
        try:
            issues, audit = await assist(doc, rev, body)
        except asyncio.CancelledError:
            update_ai(id, {"ai_status": "OUTCOME_UNKNOWN", "ai_error": store.AI_INTERRUPTED})
            raise
        except AIError as exc:
            status = "BLOCKED_EXTERNAL" if "BLOCKED_EXTERNAL" in str(exc) else ("OUTCOME_UNKNOWN" if exc.outcome_unknown else "ERROR")
            update_ai(id, {"ai_error": str(exc), "ai_status": status})
            raise HTTPException(502, str(exc)) from exc
        return update_ai(id, {"ai_status": "VERIFIED_CITATIONS_REQUIRES_REVIEW", "ai_error": None,
                              "ai_audit": {**attempt, **audit, "completed_at": now()}}, issues)

DIST = ROOT / "frontend" / "dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="frontend")
