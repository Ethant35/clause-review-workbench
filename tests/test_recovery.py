"""Offline recovery must preserve originals and never overwrite working data."""
import hashlib
import json
import sqlite3
import uuid
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from backend.workbench import store


def fixture_data(tmp_path, monkeypatch):
    root = tmp_path / "live"
    monkeypatch.setattr(store, "DATA", root)
    store.initialize()
    id = str(uuid.uuid4())
    content = b"Original agreement bytes\n"
    doc = {"id": id, "sha256": hashlib.sha256(content).hexdigest(), "name": "private.txt", "text": content.decode()}
    with store.db() as c:
        c.execute("INSERT INTO documents VALUES(?,?,?)", (id, 1, json.dumps(doc)))
    (root / "sources" / id).write_bytes(content)
    return root, id, content


def test_backup_restore_preserves_data_and_refuses_overwrite(tmp_path, monkeypatch):
    from backend.workbench.recovery import backup, restore
    root, id, content = fixture_data(tmp_path, monkeypatch)
    backup(root, tmp_path / "backup")
    restore(tmp_path / "backup", tmp_path / "restored")
    assert (tmp_path / "restored/sources" / id).read_bytes() == content
    with sqlite3.connect(tmp_path / "restored/workbench.sqlite3") as c:
        assert json.loads(c.execute("SELECT data FROM documents").fetchone()[0])["name"] == "private.txt"
    with pytest.raises(FileExistsError):
        restore(tmp_path / "backup", root)
    assert (root / "sources" / id).read_bytes() == content


def test_restore_refuses_destination_inside_backup_source(tmp_path, monkeypatch):
    from backend.workbench.recovery import backup, restore

    root, _, _ = fixture_data(tmp_path, monkeypatch)
    backup(root, tmp_path / "backup")

    with pytest.raises(ValueError, match="outside the backup directory"):
        restore(tmp_path / "backup", tmp_path / "backup" / "nested-restore")
    assert not (tmp_path / "backup" / "nested-restore").exists()


def test_corrupt_backup_leaves_destination_absent(tmp_path, monkeypatch):
    from backend.workbench.recovery import backup, restore
    root, id, _ = fixture_data(tmp_path, monkeypatch)
    backup(root, tmp_path / "backup")
    (tmp_path / "backup/sources" / id).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="hash"):
        restore(tmp_path / "backup", tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


def test_active_store_excludes_backup_and_second_server(tmp_path, monkeypatch):
    from backend.workbench.recovery import backup, exclusive_store
    root, _, _ = fixture_data(tmp_path, monkeypatch)
    with exclusive_store(root):
        with pytest.raises(RuntimeError, match="in use"):
            backup(root, tmp_path / "backup")
        with pytest.raises(RuntimeError, match="in use"):
            with exclusive_store(root):
                pass
    assert not (tmp_path / "backup").exists()


def test_symlink_source_refused(tmp_path, monkeypatch):
    from backend.workbench.recovery import backup
    root, id, content = fixture_data(tmp_path, monkeypatch)
    outside = tmp_path / "outside"; outside.write_bytes(content)
    (root / "sources" / id).unlink()
    (root / "sources" / id).symlink_to(outside)
    with pytest.raises(ValueError, match="symbolic"):
        backup(root, tmp_path / "backup")
    assert outside.read_bytes() == content


def test_missing_source_does_not_create_recovery_root(tmp_path):
    from backend.workbench.recovery import backup

    missing = tmp_path / "missing-source"
    with pytest.raises(FileNotFoundError):
        backup(missing, tmp_path / "backup")
    assert not missing.exists()
    assert not (tmp_path / "backup").exists()


def test_orphan_source_file_blocks_backup_without_deleting_it(tmp_path, monkeypatch):
    from backend.workbench.recovery import backup

    root, _, _ = fixture_data(tmp_path, monkeypatch)
    orphan = root / "sources" / "orphan-partial-upload"
    orphan.write_bytes(b"partial original source")

    with pytest.raises(ValueError, match="^Unreferenced source entry"):
        backup(root, tmp_path / "backup")

    assert orphan.read_bytes() == b"partial original source"
    assert not (tmp_path / "backup").exists()


def test_malformed_saved_json_has_controlled_content_free_error(tmp_path, monkeypatch):
    from backend.workbench.recovery import inspect

    root, id, content = fixture_data(tmp_path, monkeypatch)
    secret_marker = "private-record-marker"
    with sqlite3.connect(root / "workbench.sqlite3") as c:
        c.execute("UPDATE documents SET data=? WHERE id=?", (f'{{"secret":"{secret_marker}', id))

    with pytest.raises(ValueError, match="^Invalid saved JSON$") as error:
        inspect(root)
    assert secret_marker not in str(error.value)
    assert (root / "sources" / id).read_bytes() == content


def test_malformed_manifest_shape_is_controlled_and_does_not_create_destination(tmp_path, monkeypatch):
    from backend.workbench.recovery import backup, restore

    root, _, _ = fixture_data(tmp_path, monkeypatch)
    backup(root, tmp_path / "backup")
    (tmp_path / "backup" / "manifest.json").write_text("[]")

    with pytest.raises(ValueError, match="^Invalid backup manifest$"):
        restore(tmp_path / "backup", tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


def test_malformed_manifest_json_has_content_free_error(tmp_path, monkeypatch):
    from backend.workbench.recovery import backup, restore

    root, _, _ = fixture_data(tmp_path, monkeypatch)
    backup(root, tmp_path / "backup")
    (tmp_path / "backup" / "manifest.json").write_text('{"secret":"private-manifest-marker"')

    with pytest.raises(ValueError, match="^Invalid backup manifest$") as error:
        restore(tmp_path / "backup", tmp_path / "restored")
    assert "private-manifest-marker" not in str(error.value)
    assert not (tmp_path / "restored").exists()


def test_copy_interruption_preserves_source_and_publishes_no_backup(tmp_path, monkeypatch):
    from backend.workbench import recovery

    root, id, content = fixture_data(tmp_path, monkeypatch)

    def interrupt_copy(source, destination, **kwargs):
        Path(destination).write_bytes(b"partial copy")
        raise OSError("simulated interruption")

    monkeypatch.setattr(recovery.shutil, "copyfile", interrupt_copy)
    with pytest.raises(OSError, match="simulated interruption"):
        recovery.backup(root, tmp_path / "backup")

    assert (root / "sources" / id).read_bytes() == content
    assert not (tmp_path / "backup").exists()
    assert not list(tmp_path.glob(".crw-recovery-*"))


def test_backup_does_not_replace_destination_created_at_publish_time(tmp_path, monkeypatch):
    from backend.workbench import recovery

    root, id, content = fixture_data(tmp_path, monkeypatch)
    publish = recovery._publish_directory

    def create_destination_then_publish(staged, destination):
        Path(destination).mkdir()
        return publish(staged, destination)

    monkeypatch.setattr(recovery, "_publish_directory", create_destination_then_publish)
    with pytest.raises(FileExistsError):
        recovery.backup(root, tmp_path / "backup")

    assert list((tmp_path / "backup").iterdir()) == []
    assert (root / "sources" / id).read_bytes() == content
    assert not list(tmp_path.glob(".crw-recovery-*"))


def test_restore_holds_source_lock_through_verification_and_copy(tmp_path, monkeypatch):
    from backend.workbench import recovery

    root, _, _ = fixture_data(tmp_path, monkeypatch)
    recovery.backup(root, tmp_path / "backup")
    copy = recovery._copy_store_locked

    def assert_locked(source, destination, expected_hashes=None):
        with pytest.raises(RuntimeError, match="in use"):
            with recovery.exclusive_store(source):
                pass
        return copy(source, destination, expected_hashes)

    monkeypatch.setattr(recovery, "_copy_store_locked", assert_locked)
    recovery.restore(tmp_path / "backup", tmp_path / "restored")
    assert (tmp_path / "restored" / "workbench.sqlite3").is_file()


def test_killed_cleanup_resumes_on_restart(tmp_path, monkeypatch):
    root, id, _ = fixture_data(tmp_path, monkeypatch)
    ready = tmp_path / "committed"
    code = """import sys,time
from pathlib import Path
from backend.workbench import store
def interrupted(id):
 Path(sys.argv[2]).write_text('committed')
 time.sleep(60)
store.finish_deletion=interrupted
store.delete_document(sys.argv[1])
"""
    process = subprocess.Popen([sys.executable, "-c", code, id, str(ready)], env={**os.environ, "CRW_DATA_DIR": str(root)})
    try:
        deadline = time.monotonic() + 5
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(.01)
        assert ready.exists()
        process.kill(); process.wait(timeout=5)
        assert (root / "sources" / id).exists()
        store.initialize()
        assert not (root / "sources" / id).exists()
        assert store.get("documents", id) is None
    finally:
        if process.poll() is None:
            process.kill(); process.wait(timeout=5)


def test_null_database_identifier_fails_without_type_error(tmp_path, monkeypatch):
    from backend.workbench.recovery import inspect
    root, _, _ = fixture_data(tmp_path, monkeypatch)
    with sqlite3.connect(root / 'workbench.sqlite3') as connection:
        connection.execute("INSERT INTO documents VALUES(NULL, 1, '{}')")
    with pytest.raises(ValueError, match='Invalid source identifier'):
        inspect(root)
