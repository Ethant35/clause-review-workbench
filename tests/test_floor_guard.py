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


@pytest.mark.parametrize("replacement", ["exact", "removed", "wrong-state"])
def test_decision_copy_exception_preserves_actual_assertion(tmp_path, replacement):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)
    git("init", "-q")
    (tmp_path / "tests").mkdir()
    path = tmp_path / "tests/e2e.py"
    old = "expect(page.locator('.issue-card').nth(1).locator('.issue-status')).to_have_text('rejected')"
    new = "expect(page.locator('.issue-card').nth(1).locator('.issue-status')).to_have_text('Dismissed')"
    path.write_text(old + "\n")
    git("add", ".")
    git("-c", "user.name=Ethan", "-c", "user.email=test@example.invalid", "commit", "-qm", "baseline")
    path.write_text((new if replacement == "exact" else new.replace("Dismissed", "Confirmed") if replacement == "wrong-state" else "pass") + "\n")
    result = subprocess.run(["node", str(GUARD), "--base", "HEAD"], cwd=tmp_path, capture_output=True)
    assert result.returncode == (0 if replacement == "exact" else 1)


@pytest.mark.parametrize("replacement", ["exact", "near-miss", "removed"])
def test_native_upgrade_revision_gate_exception_is_exact(tmp_path, replacement):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)
    git("init", "-q")
    (tmp_path / "tests").mkdir()
    path = tmp_path / "tests/native_upgrade.py"
    old = "assert client.post(f'/api/documents/{doc[\"id\"]}/reviews',json={'playbook_id':'commercial'}).status_code==409"
    path.write_text(old + "\n")
    git("add", ".")
    git("-c", "user.name=Ethan", "-c", "user.email=test@example.invalid", "commit", "-qm", "baseline")
    new = [
        "extraction_is_stale=(baseline_health['extraction_revision'] != client.get('/api/health').json()['extraction_revision'])",
        "rerun_response=client.post(f'/api/documents/{doc[\"id\"]}/reviews',json={'playbook_id':'commercial'})",
        "assert rerun_response.status_code == (409 if extraction_is_stale else 201), (rerun_response.status_code, baseline_health)",
    ]
    if replacement == "exact":
        replacement_text = "\n".join(new)
    elif replacement == "near-miss":
        replacement_text = "\n".join(new[:-1] + [new[-1].replace('else 201', 'else 409')])
    else:
        replacement_text = "\n".join(new[:-1] + ["pass"])
    path.write_text(replacement_text + "\n")
    result = subprocess.run(["node", str(GUARD), "--base", "HEAD"], cwd=tmp_path, capture_output=True)
    assert result.returncode == (0 if replacement == "exact" else 1), result.stderr.decode()


@pytest.mark.parametrize("replacement", ["exact", "near-miss", "removed"])
def test_source_card_locator_exception_is_exact(tmp_path, replacement):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)
    git("init", "-q")
    (tmp_path / "tests").mkdir()
    path = tmp_path / "tests/usability_frontend.py"
    old = 'expect(page.locator(".finding-detail .source-card")).to_be_visible()'
    path.write_text(old + "\n")
    git("add", ".")
    git("-c", "user.name=Ethan", "-c", "user.email=test@example.invalid", "commit", "-qm", "baseline")
    new = 'expect(page.locator(".finding-detail .source-card").first).to_be_visible()'
    if replacement == "exact":
        replacement_text = new
    elif replacement == "near-miss":
        replacement_text = new.replace(".first", ".last")
    else:
        replacement_text = "pass"
    path.write_text(replacement_text + "\n")
    result = subprocess.run(["node", str(GUARD), "--base", "HEAD"], cwd=tmp_path, capture_output=True)
    assert result.returncode == (0 if replacement == "exact" else 1), result.stderr.decode()
