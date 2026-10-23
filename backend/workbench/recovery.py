"""Offline, same-user recovery for the supported POSIX local deployment."""
import argparse
from contextlib import closing, contextmanager
import ctypes
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import uuid


@contextmanager
def exclusive_store(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise FileNotFoundError("Recovery source directory does not exist")
    fd = os.open(root / ".store.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Data directory is in use. Stop the server before recovery or a second launch.") from exc
        yield
    finally:
        os.close(fd)


def digest(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing file or symbolic link in recovery data")
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _saved_json(value):
    try:
        if not isinstance(value, (str, bytes, bytearray)):
            raise TypeError
        return json.loads(value)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError, RecursionError):
        raise ValueError("Invalid saved JSON") from None


def _manifest(path):
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 10_000_000:
            raise ValueError
        value = _saved_json(path.read_bytes())
    except (OSError, ValueError):
        raise ValueError("Invalid backup manifest") from None
    if (not isinstance(value, dict) or type(value.get("schema")) is not int or value.get("schema") != 1
            or not isinstance(value.get("files"), dict)
            or any(not isinstance(name, str) or not isinstance(file_hash, str)
                   or len(file_hash) != 64 or any(char not in "0123456789abcdef" for char in file_hash)
                   for name, file_hash in value["files"].items())):
        raise ValueError("Invalid backup manifest")
    return value


def _publish_directory(staged, destination):
    """Atomically publish a staged directory without replacing any target."""
    staged_bytes, destination_bytes = os.fsencode(staged), os.fsencode(destination)
    if b"\0" in staged_bytes or b"\0" in destination_bytes:
        raise ValueError("Invalid recovery path")
    libc = ctypes.CDLL(None, use_errno=True)
    if os.uname().sysname == "Darwin":
        try:
            rename = libc.renamex_np
        except AttributeError:
            raise OSError(errno.ENOTSUP, "Atomic no-overwrite directory publish is unsupported") from None
        rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        result = rename(staged_bytes, destination_bytes, 0x00000004)  # RENAME_EXCL
    elif os.uname().sysname == "Linux":
        try:
            rename = libc.renameat2
        except AttributeError:
            raise OSError(errno.ENOTSUP, "Atomic no-overwrite directory publish is unsupported") from None
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        result = rename(-100, staged_bytes, -100, destination_bytes, 1)  # RENAME_NOREPLACE
    else:
        raise OSError(errno.ENOTSUP, "Atomic no-overwrite directory publish is unsupported")
    if result != 0:
        error = ctypes.get_errno()
        if error in {errno.EEXIST, errno.ENOTEMPTY}:
            raise FileExistsError(error, "Destination already exists", str(destination)) from None
        raise OSError(error, os.strerror(error), str(destination)) from None


def _copy_store_locked(source, destination, expected_hashes=None):
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Destination already exists; choose a new directory")
    if not destination.parent.is_dir():
        raise FileNotFoundError("Destination parent directory does not exist")
    hashes = inspect(source)
    if expected_hashes is not None and hashes != expected_hashes:
        raise ValueError("Backup manifest hash mismatch")
    with tempfile.TemporaryDirectory(prefix=".crw-recovery-", dir=destination.parent) as temporary:
        staged = Path(temporary) / "data"
        staged.mkdir(mode=0o700)
        (staged / "sources").mkdir(mode=0o700)
        with closing(sqlite3.connect((source / "workbench.sqlite3").as_uri() + "?mode=ro", uri=True)) as src:
            with closing(sqlite3.connect(staged / "workbench.sqlite3")) as dst:
                src.backup(dst)
        for name in hashes:
            if name.startswith("sources/"):
                shutil.copyfile(source / name, staged / name, follow_symlinks=False)
            (staged / name).chmod(0o600)
        copied = inspect(staged)
        source_hashes = {name: value for name, value in hashes.items() if name.startswith("sources/")}
        copied_source_hashes = {name: value for name, value in copied.items() if name.startswith("sources/")}
        if copied_source_hashes != source_hashes:
            raise ValueError("Recovery source changed during backup; no backup was published")
        manifest = {"schema": 1, "author": "Ethan", "files": copied}
        (staged / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (staged / "manifest.json").chmod(0o600)
        _publish_directory(staged, destination)


def inspect(root):
    """Read-only consistency check. Returns hashes, never document content."""
    root = Path(root).resolve()
    database = root / "workbench.sqlite3"
    hashes = {"workbench.sqlite3": digest(database)}
    source_dir = root / "sources"
    if source_dir.is_symlink() or not source_dir.is_dir():
        raise ValueError("Invalid or missing source directory")
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as c:
        if c.execute("PRAGMA quick_check").fetchall() != [("ok",)] or c.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Database integrity check failed")
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"documents", "reviews", "playbooks"} <= tables:
            raise ValueError("Unsupported database schema")
        if "pending_deletions" in tables and c.execute("SELECT 1 FROM pending_deletions LIMIT 1").fetchone():
            raise ValueError("Pending deletion: restart the app to finish cleanup before backup")
        if "pending_uploads" in tables and c.execute("SELECT 1 FROM pending_uploads LIMIT 1").fetchone():
            raise ValueError("Pending source copy: restart the app to finish cleanup before backup")
        for id, data in c.execute("SELECT id,data FROM documents"):
            if not isinstance(id, str) or str(uuid.UUID(id)) != id:
                raise ValueError("Invalid source identifier")
            doc = _saved_json(data)
            if not isinstance(doc, dict):
                raise ValueError("Invalid saved JSON")
            key = f"sources/{id}"
            hashes[key] = digest(root / key)
            if doc.get("sha256") != hashes[key]:
                raise ValueError("Original source hash mismatch")
        referenced_sources = {Path(name).name for name in hashes if name.startswith("sources/")}
        if any(entry.name not in referenced_sources for entry in source_dir.iterdir()):
            raise ValueError("Unreferenced source entry found; inspect manually before backup")
        # Read every saved row to detect corrupt JSON without changing history.
        for table in ("reviews", "playbooks"):
            for (data,) in c.execute(f"SELECT data FROM {table}"):
                saved = _saved_json(data)
                if not isinstance(saved, dict):
                    raise ValueError("Invalid saved JSON")
    return hashes


def backup(source, destination):
    source, destination = Path(source).resolve(), Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Destination already exists; choose a new directory")
    if destination.resolve().is_relative_to(source):
        raise ValueError("Backup must be outside the source data directory")
    with exclusive_store(source):
        _copy_store_locked(source, destination)


def restore(source, destination):
    source, destination = Path(source).resolve(), Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Restore only to a new directory")
    if destination.resolve().is_relative_to(source):
        raise ValueError("Restore destination must be outside the backup directory")
    with exclusive_store(source):
        manifest_path = source / "manifest.json"
        manifest = _manifest(manifest_path)
        hashes = inspect(source)
        if manifest["files"] != hashes:
            raise ValueError("Backup manifest hash mismatch")
        # Keep verification and copy under the same cooperating-process lock.
        # The staged copy is hashed again before its atomic publication.
        _copy_store_locked(source, destination, expected_hashes=hashes)


def main():
    parser = argparse.ArgumentParser(description="Offline workbench backup, restore and integrity checks. Stop the server first.")
    parser.add_argument("command", choices=["backup", "restore", "doctor"])
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path, nargs="?")
    args = parser.parse_args()
    try:
        if args.command == "doctor":
            with exclusive_store(args.source):
                files = inspect(args.source)
            print(json.dumps({"status": "ok", "source_count": len(files) - 1, "author": "Ethan"}))
        else:
            if args.destination is None:
                parser.error("backup and restore require a new destination directory")
            (backup if args.command == "backup" else restore)(args.source, args.destination)
            print(json.dumps({"status": "ok", "operation": args.command, "author": "Ethan"}))
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        # Stable error classes only: exception text can contain private paths/data.
        print(json.dumps({"status": "error", "code": type(exc).__name__, "help": "Check the recovery guide, permissions, free disk space, and that the server is stopped."}))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
