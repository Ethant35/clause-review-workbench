"""Single-user local storage; short transactions and cascading review deletion."""
import json
import hashlib
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

AI_INTERRUPTED = "AI assistance was interrupted. A provider charge may have occurred. Check provider activity before retrying; no automatic retry was made. Your offline review is preserved."

data_setting = os.environ.get("CRW_DATA_DIR", ".data")
if not data_setting.strip():
    raise ValueError("CRW_DATA_DIR must be a nonempty directory")
DATA = Path(data_setting).resolve()
try:
    RETENTION_DAYS = int(os.environ.get("CRW_RETENTION_DAYS", "0"))
    if not 0 <= RETENTION_DAYS <= 36500:
        raise ValueError()
except ValueError as exc:
    raise ValueError("CRW_RETENTION_DAYS must be 0 (disabled) or 1 through 36500") from exc

def initialize():
    DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
    if DATA.stat().st_mode & 0o077:
        raise ValueError("CRW_DATA_DIR must be private (chmod 700); existing permissions were not changed")
    if (DATA / "sources").is_symlink() or (DATA / "workbench.sqlite3").is_symlink():
        raise ValueError("Storage files/directories must not be symbolic links")
    (DATA / "sources").mkdir(mode=0o700, exist_ok=True)
    with db() as c:
        c.executescript('''
          CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, created REAL NOT NULL, data TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS playbooks (id TEXT PRIMARY KEY, data TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS reviews (id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE, data TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS pending_deletions (id TEXT PRIMARY KEY);
          CREATE TABLE IF NOT EXISTS pending_uploads (id TEXT PRIMARY KEY);
          CREATE INDEX IF NOT EXISTS documents_created ON documents(created DESC, id DESC);
          CREATE INDEX IF NOT EXISTS reviews_document ON reviews(document_id);
        ''')
        c.execute("UPDATE reviews SET data=json_set(data, '$.ai_status', 'OUTCOME_UNKNOWN', '$.ai_error', ?) WHERE json_extract(data, '$.ai_status')='IN_PROGRESS'", (AI_INTERRUPTED,))
    (DATA / "workbench.sqlite3").chmod(0o600)
    retry_deletions()
    retry_pending_uploads()
    purge_expired()

@contextmanager
def db():
    c = sqlite3.connect(DATA / "workbench.sqlite3", timeout=5)
    try:
        with c:
            c.execute("PRAGMA foreign_keys=ON")
            c.execute("PRAGMA secure_delete=ON")
            yield c
    finally:
        c.close()

def source_path(id):
    if str(uuid.UUID(id)) != id:
        raise ValueError("Invalid source identifier")
    path = DATA / "sources" / id
    if path.is_symlink() or path.parent.resolve() != DATA / "sources":
        raise ValueError("Unsafe source path")
    return path

def finish_deletion(id):
    source_path(id).unlink(missing_ok=True)
    with db() as c:
        c.execute("DELETE FROM pending_deletions WHERE id=?", (id,))

def retry_deletions():
    with db() as c:
        ids = c.execute("SELECT id FROM pending_deletions").fetchall()
    for (id,) in ids:
        finish_deletion(id)

def retry_pending_uploads():
    """Clean interrupted unpublished copies during exclusive app startup only."""
    with db() as c:
        ids = c.execute("SELECT id FROM pending_uploads").fetchall()
    for (id,) in ids:
        source = source_path(id)
        with db() as c:
            row = c.execute("SELECT data FROM documents WHERE id=?", (id,)).fetchone()
        if row:
            # The document row and removal of its marker commit together. If a
            # DB status was ambiguous, preserve a complete published source.
            doc = json.loads(row[0])
            try:
                intact = hashlib.sha256(source.read_bytes()).hexdigest() == doc.get("sha256")
            except OSError:
                intact = False
            if not intact:
                raise ValueError("Published source with pending upload marker failed integrity check")
        else:
            source.unlink(missing_ok=True)
        with db() as c:
            c.execute("DELETE FROM pending_uploads WHERE id=?", (id,))

def delete_document(id):
    source_path(id)  # Validate before committing any change.
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        exists = c.execute("SELECT 1 FROM documents WHERE id=?", (id,)).fetchone()
        pending = c.execute("SELECT 1 FROM pending_deletions WHERE id=?", (id,)).fetchone()
        if not exists and not pending:
            return False
        c.execute("INSERT OR IGNORE INTO pending_deletions VALUES(?)", (id,))
        c.execute("DELETE FROM documents WHERE id=?", (id,))
    # Commit the durable cleanup intent before touching the original. A rollback
    # preserves it; a crash or unlink failure is retried at startup/retention.
    finish_deletion(id)
    return True

def purge_expired():
    retry_deletions()
    if RETENTION_DAYS <= 0:
        return
    with db() as c:
        ids = c.execute("SELECT id FROM documents WHERE created < ?", (time.time() - RETENTION_DAYS * 86400,)).fetchall()
    for (id,) in ids:
        delete_document(id)

def get(table, id):
    assert table in {"documents", "reviews", "playbooks"}
    with db() as c:
        row = c.execute(f"SELECT data FROM {table} WHERE id=?", (id,)).fetchone()
    return json.loads(row[0]) if row else None
