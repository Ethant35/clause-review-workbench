"""Author: Ethan. Reproducible-input Apple Silicon app assembly; signing is explicit."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tarfile
import tempfile
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'artifacts/native-runtime'
INSTALL_SHA = '3ee3ee547cedfeb7c2b16b2b7156039f7b470bb8f857e226fd3d2eb11db83c76'
FULL_SHA = 'dbefa04d4107b449e17022f9c78d3eacbd37a1aa8c166c6220dbd95addf3f318'
BASE = 'https://github.com/astral-sh/python-build-standalone/releases/download/20260901/'
INSTALL = 'cpython-3.12.14%2B20260901-aarch64-apple-darwin-install_only.tar.gz'
FULL = 'cpython-3.12.14%2B20260901-aarch64-apple-darwin-pgo%2Blto-full.tar.zst'

def run(*args, **kwargs):
    subprocess.run([str(x) for x in args], cwd=ROOT, check=True, **kwargs)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def download(name, url, expected):
    path = CACHE / name
    if not path.exists():
        run('curl', '-fLsS', '--retry', '2', url, '-o', path)
    if sha(path) != expected:
        raise ValueError(f'Runtime checksum mismatch: {name}')
    return path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True, help='New .app path; existing paths are never replaced')
    parser.add_argument('--sign', help='Developer ID Application identity; omitted for test assembly')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or output.is_symlink() or output.suffix != '.app':
        raise ValueError('Choose a new .app output path')
    if os.uname().machine != 'arm64':
        raise ValueError('Build on an Apple Silicon Mac')
    CACHE.mkdir(parents=True, exist_ok=True)
    install = download('python-install.tar.gz', BASE + INSTALL, INSTALL_SHA)
    full = download('python-full.tar.zst', BASE + FULL, FULL_SHA)
    destination = output
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.native-build-', dir=destination.parent) as staging:
        output = Path(staging) / destination.name
        contents = output / 'Contents'
        resources = contents / 'Resources'
        macos = contents / 'MacOS'
        resources.mkdir(parents=True); macos.mkdir()
        with tarfile.open(install) as archive:
            archive.extractall(resources, filter='data')
        # License texts from the identical upstream build accompany its runtime.
        notices = resources / 'python-build-notices'; notices.mkdir()
        run('tar', '-xf', full, '-C', notices, 'python/PYTHON.json', 'python/licenses')
        requirements = CACHE / 'requirements.txt'
        run('uv', 'export', '--frozen', '--no-dev', '--no-emit-project', '--format', 'requirements-txt', '--output-file', requirements, stdout=subprocess.DEVNULL)
        python = resources / 'python/bin/python3'
        site = resources / 'python/lib/python3.12/site-packages'
        run('uv', 'pip', 'install', '--python', python, '--target', site, '--require-hashes', '--only-binary', ':all:', '-r', requirements)
        workbench = resources / 'workbench'; workbench.mkdir()
        sources = []
        for path in sorted((ROOT / 'backend').rglob('*.py')):
            if '__pycache__' not in path.parts and ' ' not in path.name:
                sources.append(path)
        sources += sorted((ROOT / 'playbooks').glob('*.yaml'))
        sources += [ROOT / name for name in ('LICENSE','README.md','PRIVACY.md','SECURITY.md','THIRD_PARTY_NOTICES.md','pyproject.toml','uv.lock')]
        for path in sources:
            target = workbench / path.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(path,target)
        shutil.copytree(ROOT / 'licenses', workbench / 'licenses')
        shutil.copytree(ROOT / 'docs', workbench / 'docs')
        shutil.copytree(ROOT / 'frontend/dist', workbench / 'frontend/dist')
        shutil.copy2(ROOT / 'native/bootstrap.py', resources / 'bootstrap.py')
        run('xcrun', 'swiftc', '-swift-version', '5', '-O', '-target', 'arm64-apple-macosx13.0', ROOT / 'native/Workbench.swift', '-o', macos / 'Workbench')
        version = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']['version']
        info = {'CFBundleName':'Clause Review Workbench','CFBundleDisplayName':'Clause Review Workbench','CFBundleIdentifier':'com.ethantarnarider.clause-review-workbench','CFBundleVersion':version,'CFBundleShortVersionString':version,'CFBundleExecutable':'Workbench','CFBundlePackageType':'APPL','LSMinimumSystemVersion':'13.0','NSHighResolutionCapable':True,'NSHumanReadableCopyright':'Copyright © Ethan. Third-party notices are included.','NSPrincipalClass':'NSApplication'}
        (contents / 'Info.plist').write_bytes(plistlib.dumps(info))
        manifest = {'author':'Ethan','version':version,'architecture':'arm64','runtime_build':'20260901','runtime_version':'3.12.14','runtime_url':BASE + INSTALL,'runtime_sha256':INSTALL_SHA,'runtime_notices_url':BASE + FULL,'runtime_notices_sha256':FULL_SHA,'source_files':{str(p.relative_to(ROOT)):sha(p) for p in sources},'requirements_sha256':sha(requirements)}
        (resources / 'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        if args.sign:
            # Fresh build artifacts only: Finder metadata is not signable code.
            # Never clear quarantine on downloaded distributions during acceptance.
            run('xattr', '-cr', output)
            magic = {bytes.fromhex(x) for x in ('feedface','cefaedfe','feedfacf','cffaedfe','cafebabe','bebafeca','cafebabf','bfbafeca')}
            for path in sorted(output.rglob('*'), key=lambda p:len(p.parts), reverse=True):
                if path == macos / 'Workbench':
                    continue
                if path.is_file() and not path.is_symlink():
                    with path.open('rb') as stream:
                        native = stream.read(4) in magic
                    if native:
                        run('codesign','--force','--options','runtime','--timestamp','--sign',args.sign,path)
            run('xattr', '-cr', output)
            run('codesign','--force','--options','runtime','--timestamp','--sign',args.sign,output)
            run('codesign','--verify','--deep','--strict','--verbose=2',output)
        sys.path.insert(0, str(ROOT))
        from backend.workbench.recovery import _publish_directory
        _publish_directory(output, destination)
    print(destination)

if __name__ == '__main__':
    main()
