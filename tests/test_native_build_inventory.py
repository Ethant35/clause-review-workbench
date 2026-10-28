"""Author: Ethan. Keep native bundle inputs aligned with the source package."""
import importlib.util
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('build_macos', ROOT / 'scripts/build_macos.py')
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


def _write(root, relative, text='fixture\n'):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _required_tree(root):
    for name in ('LICENSE', 'README.md', 'PRIVACY.md', 'SECURITY.md',
                 'THIRD_PARTY_NOTICES.md', 'pyproject.toml', 'uv.lock'):
        _write(root, name)
    _write(root, 'docs/guide.md')
    _write(root, 'licenses/package/LICENSE')
    _write(root, 'backend/workbench/main.py')
    _write(root, 'playbooks/commercial.yaml')


def test_git_inventory_includes_staged_docs_and_excludes_untracked_sync_duplicates(tmp_path):
    _required_tree(tmp_path)
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    subprocess.run(['git', '-C', str(tmp_path), 'add', '.'], check=True)
    _write(tmp_path, 'docs/new-review-flow.md')
    subprocess.run(['git', '-C', str(tmp_path), 'add', 'docs/new-review-flow.md'], check=True)
    untracked_docs = _write(tmp_path, 'docs/readiness 2.md')
    untracked_license = _write(tmp_path, 'licenses/package/LICENSE 2')
    _write(tmp_path, 'backend/workbench/local 2.py')
    _write(tmp_path, 'evidence/private.json')

    bundled = set(BUILD.bundle_sources(tmp_path))

    assert tmp_path / 'docs/new-review-flow.md' in bundled
    assert tmp_path / 'docs/guide.md' in bundled
    assert tmp_path / 'licenses/package/LICENSE' in bundled
    assert tmp_path / 'backend/workbench/main.py' in bundled
    assert tmp_path / 'playbooks/commercial.yaml' in bundled
    assert untracked_docs not in bundled
    assert untracked_license not in bundled
    assert tmp_path / 'backend/workbench/local 2.py' not in bundled
    assert tmp_path / 'evidence/private.json' not in bundled


def test_source_tree_fallback_selects_only_bundle_inputs(tmp_path):
    _required_tree(tmp_path)
    _write(tmp_path, 'docs/guide 2.md')
    _write(tmp_path, 'licenses/package/LICENSE 2')
    _write(tmp_path, 'backend/workbench/engine.py')
    _write(tmp_path, 'playbooks/nda.yaml')
    _write(tmp_path, 'tests/test_unrelated.py')
    _write(tmp_path, 'evidence/report.json')

    bundled = set(BUILD.bundle_sources(tmp_path))

    assert tmp_path / 'docs/guide 2.md' in bundled
    assert tmp_path / 'licenses/package/LICENSE 2' in bundled
    assert tmp_path / 'backend/workbench/engine.py' in bundled
    assert tmp_path / 'playbooks/nda.yaml' in bundled
    assert tmp_path / 'tests/test_unrelated.py' not in bundled
    assert tmp_path / 'evidence/report.json' not in bundled
