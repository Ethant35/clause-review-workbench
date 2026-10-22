"""Single-user local storage; short transactions and cascading review deletion."""
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

DATA = Path(os.environ.get("CRW_DATA_DIR", ".data")).resolve()
RETENTION_DAYS = int(os.environ.get("CRW_RETENTION_DAYS", "0"))

def initialize():
    DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
    (DATA / "sources").mkdir(mode=0o700, exist_ok=True)
    with db() as c:
        c.executescript('''
          CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, created REAL NOT NULL, data TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS playbooks (id TEXT PRIMARY KEY, data TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS reviews (id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE, data TEXT NOT NULL);
        ''')
    (DATA / "workbench.sqlite3").chmod(0o600)
    purge_expired()

@contextmanager
def db():
    with sqlite3.connect(DATA / "workbench.sqlite3", timeout=15) as c:
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA secure_delete=ON")
        yield c

def delete_document(id):
    with db() as c:
        if not c.execute("SELECT 1 FROM documents WHERE id=?", (id,)).fetchone():
            return False
        # Sources have UUID names only. IDs are read from database, never user paths.
        (DATA / "sources" / id).unlink(missing_ok=True)
        c.execute("DELETE FROM documents WHERE id=?", (id,))
    return True

def purge_expired():
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
