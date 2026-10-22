"""Upgrade a database created by the real v1.0.0 server, without fabricating rows."""
from datetime import datetime, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import signal
import socket
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time

import httpx
from docx import Document
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts'
OUT.mkdir(exist_ok=True)
RUN = Path(tempfile.mkdtemp(prefix='upgrade-', dir=OUT))
OLD = RUN / 'v1.0.0'
OLD.mkdir()
with tarfile.open(fileobj=BytesIO(subprocess.check_output(['git', 'archive', 'v1.0.0'], cwd=ROOT))) as archive:
    archive.extractall(OLD, filter='data')
DATA = RUN / 'data'
NETWORK = RUN / 'network.jsonl'
NETWORK.touch()
REGISTRY = Path(os.environ.get('CRW_PROCESS_REGISTRY', OUT / 'processes.json'))
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    PORT = sock.getsockname()[1]
BASE = f'http://127.0.0.1:{PORT}'
process = None
log = (RUN / 'server.log').open('w')
results = []


def stop():
    global process
    if process and process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=10)
    process = None
    REGISTRY.write_text('[]')


def start(root):
    global process
    stop()
    env = os.environ.copy()
    env.pop('OPENROUTER_API_KEY', None)
    env.update(CRW_DATA_DIR=str(DATA), CRW_PORT=str(PORT), CRW_NETWORK_AUDIT=str(NETWORK))
    process = subprocess.Popen([sys.executable, 'tests/serve_checked.py'], cwd=root, env=env,
                               stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    REGISTRY.write_text(json.dumps([os.getpgrp(), process.pid]))
    for _ in range(100):
        try:
            if client.get('/api/health').status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(.1)
    raise RuntimeError('Server did not start')


def payload(response):
    response.raise_for_status()
    return response.json()


def stored():
    with sqlite3.connect(DATA / 'workbench.sqlite3') as connection:
        return {table: connection.execute(f'SELECT * FROM {table} ORDER BY id').fetchall()
                for table in ('documents', 'reviews')}


def passed(name):
    results.append({'id': name, 'status': 'PASS'})
    print(name, 'PASS', flush=True)


try:
    with httpx.Client(base_url=BASE, timeout=30, trust_env=False) as client:
        start(OLD)
        source = b'Each party is not required to protect the other party confidential information.\n'
        document = payload(client.post('/api/documents', files={'file': ('historical.txt', source)}))
        did = document['id']
        review = payload(client.post(f'/api/documents/{did}/reviews', json={'playbook_id': 'commercial'}))
        rid = review['id']
        assert next(c for c in review['checks'] if c['rule_id'] == 'confidentiality-mutual')['outcome'] == 'COMPLIANT'
        issue = review['issues'][0]
        # Use the actual request field names from the released public API.
        decision = {'status': 'accepted', 'notes': 'Historical reviewer decision; preserve this note.'}
        saved = payload(client.patch(f"/api/reviews/{rid}/issues/{issue['id']}", json=decision))
        assert saved['notes'] == decision['notes']
        before = stored()
        stop()
        start(ROOT)
        assert stored() == before
        assert client.get(f'/api/documents/{did}/original').content == source
        historical = payload(client.get(f'/api/reviews/{rid}'))
        assert historical['verification_status'] == 'HISTORICAL_UNVERIFIED'
        assert historical['issues'][0]['notes'] == decision['notes']
        assert payload(client.get(f'/api/documents/{did}/reviews'))[0]['verification_warning']
        passed('UP-01-preserve-original-rows-decisions-and-source')
        assert client.post(f'/api/documents/{did}/reviews', json={'playbook_id': 'commercial'}).status_code == 409
        assert client.post(f'/api/reviews/{rid}/ai', json={'consent': True, 'model': 'openai/gpt-4o-mini', 'provider': 'OpenAI'}).status_code == 409
        passed('UP-02-prevent-old-extraction-reuse-and-ai-transmission')
        for fmt, ext in [('json', 'json'), ('markdown', 'md'), ('docx', 'docx')]:
            response = client.get(f'/api/reviews/{rid}/export', params={'format': fmt})
            response.raise_for_status()
            (RUN / f'historical.{ext}').write_bytes(response.content)
            if fmt == 'docx':
                doc = Document(BytesIO(response.content))
                text = '\n'.join(p.text for p in doc.paragraphs)
                assert doc.core_properties.author == doc.core_properties.last_modified_by == 'Ethan'
            else:
                text = response.text
            assert 'Historical review: not verified' in text
        assert stored() == before
        passed('UP-03-all-exports-label-historical-results')
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={'width': 1440, 'height': 1100})
            page.goto(BASE)
            expect(page.get_by_text('Historical review: not verified', exact=False)).to_be_visible()
            expect(page.get_by_role('button', name='Run review', exact=True)).to_be_disabled()
            page.screenshot(path=str(RUN / 'historical-review.png'), full_page=True)
            passed('UP-04-browser-warning-and-disabled-review')
            page.locator('.upload-box input').set_input_files({'name': 'reuploaded.txt', 'mimeType': 'text/plain', 'buffer': source})
            expect(page.get_by_role('heading', level=2, name='reuploaded.txt')).to_be_visible()
            page.get_by_role('button', name='Run review', exact=True).click()
            expect(page.get_by_text('Review complete.', exact=True)).to_be_visible()
            page.screenshot(path=str(RUN / 'current-review.png'), full_page=True)
            browser.close()
        fresh = next(d for d in payload(client.get('/api/documents')) if d['name'] == 'reuploaded.txt')
        current = payload(client.get(f"/api/documents/{fresh['id']}/reviews"))[0]
        assert current['verification_status'] == 'CURRENT_CHECKS' and current['review_revision'] == 2
        assert next(c for c in current['checks'] if c['rule_id'] == 'confidentiality-mutual')['outcome'] == 'NEEDS_REVIEW'
        after = stored()
        assert all(row in after[table] for table, rows in before.items() for row in rows)
        assert client.get(f"/api/documents/{fresh['id']}/original").content == source
        passed('UP-05-browser-reupload-new-checks-preserve-history')
        assert NETWORK.read_text() == ''
        passed('UP-06-no-backend-outbound-connections')
finally:
    stop()
    log.close()
    (OUT / 'upgrade-results.json').write_text(json.dumps({'author': 'Ethan', 'timestamp': datetime.now(timezone.utc).isoformat(),
        'baseline': 'v1.0.0', 'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'run': str(RUN.relative_to(ROOT)), 'results': results, 'status': 'PASS' if len(results) == 6 else 'FAIL'}, indent=2) + '\n')
