"""Bounded local events and admission controls. No source or request payload logs."""
from datetime import datetime, timezone
import logging
import os
from logging.handlers import RotatingFileHandler
import time
import uuid

from starlette.responses import JSONResponse

LOG = logging.getLogger("workbench.local")
LOG.propagate = False
LOG.addHandler(logging.NullHandler())
HEADERS = {
    b"cache-control": b"no-store", b"x-content-type-options": b"nosniff",
    b"referrer-policy": b"no-referrer",
    b"content-security-policy": b"default-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'",
}


class QuietRotatingHandler(RotatingFileHandler):
    def _open(self):
        fd = os.open(self.baseFilename, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        return os.fdopen(fd, "a", encoding="utf-8")

    def handleError(self, record):
        # Storage failure must not print private paths or recursively log failures.
        pass


def close():
    for handler in list(LOG.handlers):
        handler.close()
        LOG.removeHandler(handler)
    LOG.addHandler(logging.NullHandler())


def configure(root, max_bytes=1_000_000, backups=2):
    close()
    path = root / "diagnostics.jsonl"
    if any(p.is_symlink() for p in root.glob("diagnostics.jsonl*")):
        raise ValueError("Diagnostics files must not be symbolic links")
    path.touch(mode=0o600, exist_ok=True)
    path.chmod(0o600)
    handler = QuietRotatingHandler(path, maxBytes=max_bytes, backupCount=backups)
    handler.setFormatter(logging.Formatter("%(message)s"))
    LOG.addHandler(handler)
    LOG.setLevel(logging.INFO)


def event(name, *, request_id, entry_point, status, route, duration_ms):
    import json
    LOG.info(json.dumps({"time": datetime.now(timezone.utc).isoformat(), "event": name,
                         "request_id": request_id, "entry_point": entry_point,
                         "status": status, "route": route, "duration_ms": duration_ms}))


class LocalBoundary:
    """One event loop, bounded active work; reject before multipart body parsing."""
    def __init__(self, app, max_active=16):
        self.app, self.max_active, self.active = app, max_active, 0
        self.groups = {"upload": 0, "review": 0, "ai": 0}

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request_id, started = str(uuid.uuid4()), time.perf_counter()
        status, response_started = 500, False
        async def secured(message):
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                status, response_started = message["status"], True
                headers = [(k, v) for k, v in message.get("headers", []) if k.lower() not in HEADERS]
                message = {**message, "headers": headers + list(HEADERS.items()) + [(b"x-request-id", request_id.encode())]}
            await send(message)
        path = scope.get("path", "")
        group = None
        if scope.get("method") == "POST":
            if path == "/api/documents": group = "upload"
            elif path.startswith("/api/documents/") and path.endswith("/reviews"): group = "review"
            elif path.startswith("/api/reviews/") and path.endswith("/ai"): group = "ai"
        rejected = self.active >= self.max_active or (group and self.groups[group] >= (1 if group == "ai" else 2))
        if not rejected:
            self.active += 1
            if group: self.groups[group] += 1
        try:
            if rejected:
                await JSONResponse({"detail": "Local work limit reached. Wait for the current operation, then retry."}, 503, headers={"Retry-After": "2"})(scope, receive, secured)
            else:
                await self.app(scope, receive, secured)
        except Exception:
            if not response_started:
                await JSONResponse({"detail": "Local operation failed. Check storage space and permissions; use the recovery guide."}, 503)(scope, receive, secured)
            # A started response cannot be replaced safely; stop the stream.
            else:
                raise
        finally:
            if not rejected:
                self.active -= 1
                if group: self.groups[group] -= 1
            route = getattr(scope.get("route"), "path", "unmatched")
            event("request", request_id=request_id, entry_point="http", status=status,
                  route=route, duration_ms=round((time.perf_counter() - started) * 1000, 2))
