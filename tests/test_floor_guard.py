"""Mutation controls for the local diff guard; no hooks or CI installation."""
from pathlib import Path
import subprocess

import pytest

GUARD = Path(__file__).resolve().parents[1] / "scripts/floor-guard.mjs"


@pytest.mark.parametrize("mutation", ["skip", "assertion", "suppression", "stub", "threshold", "exception", "deleted"])
def test_guard_blocks_weakened_changes(tmp_path, mutation):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)
    git("init", "-q")
    (tmp_path / "test_contract.py").write_text("def test_required():\n    assert 2 == 2\n")
    (tmp_path / "CONSTRAINTS.md").write_text("- Size: at most 10 files\n")
    git("add", ".")
    git("-c", "user.name=Ethan", "-c", "user.email=test@example.invalid", "commit", "-qm", "baseline")
    command = ["node", str(GUARD), "--base", "HEAD"]
    (tmp_path / "style.css").write_text(".skip-link { color: black; }\n")
    assert subprocess.run(command, cwd=tmp_path, capture_output=True).returncode == 0
    if mutation == "skip": (tmp_path / "test_new.py").write_text("@pytest.mark.skip\ndef test_x(): pass\n")
    elif mutation == "assertion": (tmp_path / "test_contract.py").write_text("def test_required():\n    pass\n")
    elif mutation == "suppression": (tmp_path / "new.py").write_text("x = 1  # noqa\n")
    elif mutation == "stub": (tmp_path / "new.py").write_text("# TODO finish\n")
    elif mutation == "threshold": (tmp_path / "CONSTRAINTS.md").write_text("- Size: at most 100 files\n")
    elif mutation == "exception": (tmp_path / "CONSTRAINTS.md").write_text("- Size: at most 10 files\n| E1 | permit failure |\n")
    else: (tmp_path / "test_contract.py").unlink()
    assert subprocess.run(command, cwd=tmp_path, capture_output=True).returncode == 1
    assert subprocess.run(["node", str(GUARD), "--base", "missing-ref"], cwd=tmp_path, capture_output=True).returncode == 2


@pytest.mark.parametrize("replacement", ["exact", "missing", "different"])
def test_status_locator_exception_requires_exact_replacement(tmp_path, replacement):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)
    git("init", "-q")
    (tmp_path / "tests").mkdir()
    path = tmp_path / "tests/e2e.py"
    path.write_text("expect(page.get_by_role('status')).to_contain_text('Reviewer update saved locally.')\n")
    git("add", ".")
    git("-c", "user.name=Ethan", "-c", "user.email=test@example.invalid", "commit", "-qm", "baseline")
    new = "expect(page.get_by_role('status').filter(has_text='Reviewer update saved locally.')).to_be_visible()\n"
    path.write_text(new if replacement == "exact" else new.replace("to_be_visible()", "to_be_hidden()") if replacement == "different" else "pass\n")
    result = subprocess.run(["node", str(GUARD), "--base", "HEAD"], cwd=tmp_path, capture_output=True)
    assert result.returncode == (0 if replacement == "exact" else 1)
