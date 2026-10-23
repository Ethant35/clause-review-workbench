import os
from pathlib import Path
import subprocess
import sys

import pytest


BOOTSTRAP = Path(__file__).resolve().parents[1] / "native" / "bootstrap.py"


@pytest.mark.parametrize("command", ["serve", "recover"])
def test_bootstrap_rejects_stale_expected_parent_before_startup_side_effects(tmp_path, command):
    data_dir = tmp_path / "must-not-be-created"
    environment = os.environ.copy()
    environment.update(
        CRW_EXPECTED_PARENT_PID="2147483647",
        CRW_DATA_DIR=str(data_dir),
        CRW_PORT="1",
    )
    result = subprocess.run(
        [sys.executable, str(BOOTSTRAP), command, "doctor", str(data_dir)]
        if command == "recover"
        else [sys.executable, str(BOOTSTRAP), command],
        env=environment,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode != 0
    assert "Launching app is no longer running" in result.stderr
    assert not data_dir.exists()
