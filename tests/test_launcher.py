import os
import shutil
from pathlib import Path
import socket
import subprocess
import time

import pytest

from backend.workbench import launcher


def test_settings_validate_port_and_retention_without_echoing_values():
    with pytest.raises(launcher.LauncherError, match="CRW_PORT") as port_error:
        launcher.parse_settings({"CRW_PORT": "8765;private-token"})
    assert "private-token" not in str(port_error.value)

    with pytest.raises(launcher.LauncherError, match="CRW_RETENTION_DAYS"):
        launcher.parse_settings({"CRW_RETENTION_DAYS": "-1"})
    with pytest.raises(launcher.LauncherError, match="CRW_DATA_DIR"):
        launcher.parse_settings({"CRW_DATA_DIR": "   "})

    assert launcher.parse_settings({}).port == 8765
    assert launcher.parse_settings({"CRW_RETENTION_DAYS": "36500"}).retention_days == 36500


def test_frontend_preflight_checks_index_and_referenced_assets(tmp_path):
    dist = tmp_path / "frontend" / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text('<script src="/assets/app.js"></script>')

    with pytest.raises(launcher.LauncherError, match="Built frontend"):
        launcher.check_frontend_build(tmp_path)

    (dist / "assets" / "app.js").write_text("// built")
    launcher.check_frontend_build(tmp_path)


def test_data_preflight_creates_private_leaf_and_does_not_change_existing_mode(tmp_path):
    new_data = tmp_path / "new" / "private-data"
    launcher.prepare_data_directory(str(new_data))
    assert new_data.stat().st_mode & 0o777 == 0o700

    existing = tmp_path / "existing"
    existing.mkdir(mode=0o755)
    with pytest.raises(launcher.LauncherError, match="private permissions"):
        launcher.prepare_data_directory(str(existing))
    assert existing.stat().st_mode & 0o777 == 0o755


def test_startup_error_messages_are_safe_and_actionable(tmp_path):
    lock_message = launcher.startup_diagnostic(RuntimeError("Data directory is in use. Stop before starting"))
    assert "already in use" in lock_message
    assert str(tmp_path) not in lock_message

    corrupt = launcher.startup_diagnostic(Exception(f"file is not a database at {tmp_path}/private.sqlite"))
    assert "Startup failed" in corrupt
    assert str(tmp_path) not in corrupt
    assert "private.sqlite" not in corrupt


@pytest.mark.parametrize("frontend_present", [False, True])
def test_missing_python_environment_is_actionable_and_does_not_sync(tmp_path, frontend_present):
    project = Path(__file__).resolve().parents[1]
    (tmp_path / "scripts").mkdir()
    shutil.copy2(project / "scripts" / "start.sh", tmp_path / "scripts" / "start.sh")
    if frontend_present:
        (tmp_path / "frontend" / "dist").mkdir(parents=True)
        (tmp_path / "frontend" / "dist" / "index.html").write_text("Existing build")
    environment = os.environ.copy()
    environment["PATH"] = "/usr/bin:/bin"
    result = subprocess.run(
        [str(tmp_path / "scripts" / "start.sh")],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "Project Python environment is missing" in result.stderr
    assert "uv sync --frozen --python 3.12 --no-dev" in result.stderr
    assert "docs/startup.md" in result.stderr
    assert ("Built frontend is missing" in result.stderr) is (not frontend_present)
    if not frontend_present:
        assert "npm --prefix frontend ci && npm --prefix frontend run build" in result.stderr
    assert not (tmp_path / ".venv").exists()
    assert not (tmp_path / ".data").exists()
    assert "Traceback" not in result.stderr


def test_start_script_runs_existing_environment_without_uv_and_stays_loopback(tmp_path):
    project = Path(__file__).resolve().parents[1]
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    data_dir = tmp_path / "private-data"
    environment = os.environ.copy()
    environment.update(
        PATH="/usr/bin:/bin",
        CRW_PORT=str(port),
        CRW_DATA_DIR=str(data_dir),
        CRW_RETENTION_DAYS="0",
    )
    process = subprocess.Popen(
        [str(project / "scripts" / "start.sh")],
        cwd=project,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.monotonic() + 12
        response = b""
        while time.monotonic() < deadline:
            if process.poll() is not None:
                break
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2) as client:
                    client.sendall(b"GET /api/health HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n")
                    chunks = []
                    while chunk := client.recv(4096):
                        chunks.append(chunk)
                    response = b"".join(chunks)
                    break
            except OSError:
                time.sleep(0.05)
        assert b"200 OK" in response
        assert b'"status":"ok"' in response
    finally:
        process.terminate()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)


def test_busy_port_has_safe_diagnostic(tmp_path):
    project = Path(__file__).resolve().parents[1]
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        environment = os.environ.copy()
        environment.update(CRW_PORT=str(port), CRW_DATA_DIR=str(tmp_path / "not-created"))
        result = subprocess.run(
            [str(project / ".venv" / "bin" / "python"), "-m", "backend.workbench.launcher"],
            cwd=project,
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
        )
    assert result.returncode == 2
    assert "CRW_PORT is already in use" in result.stderr
    assert "address already in use" not in result.stderr.lower()
    assert str(tmp_path) not in result.stderr


def test_data_lock_has_safe_diagnostic(tmp_path):
    from backend.workbench.recovery import exclusive_store

    project = Path(__file__).resolve().parents[1]
    data_dir = tmp_path / "private-data"
    data_dir.mkdir(mode=0o700)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    environment = os.environ.copy()
    environment.update(CRW_PORT=str(port), CRW_DATA_DIR=str(data_dir))
    with exclusive_store(data_dir):
        result = subprocess.run(
            [str(project / ".venv" / "bin" / "python"), "-m", "backend.workbench.launcher"],
            cwd=project,
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
        )
    assert result.returncode == 1
    assert "Data directory is already in use" in result.stderr
    assert "Traceback" not in result.stderr
    assert str(data_dir) not in result.stderr


def test_corrupt_database_has_safe_diagnostic(tmp_path):
    project = Path(__file__).resolve().parents[1]
    data_dir = tmp_path / "private-data"
    data_dir.mkdir(mode=0o700)
    database = data_dir / "workbench.sqlite3"
    database.write_bytes(b"not a sqlite database")
    database.chmod(0o600)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    environment = os.environ.copy()
    environment.update(CRW_PORT=str(port), CRW_DATA_DIR=str(data_dir))
    result = subprocess.run(
        [str(project / ".venv" / "bin" / "python"), "-m", "backend.workbench.launcher"],
        cwd=project,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 1
    assert "Saved local data could not be opened" in result.stderr
    assert "Traceback" not in result.stderr
    assert str(project) not in result.stderr
    assert str(data_dir) not in result.stderr
    assert "not a database" not in result.stderr
