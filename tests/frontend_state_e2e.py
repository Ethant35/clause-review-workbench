"""Real browser selection race using a held invalid AI request and no provider call.

Author: Ethan. A synthetic key enables the UI; invalid model syntax must fail
request validation before the provider adapter can run. Network audit must stay empty.
"""
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time

import httpx
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
(ROOT / 'artifacts/readiness').mkdir(parents=True, exist_ok=True)
RUN = Path(tempfile.mkdtemp(prefix='frontend-state-', dir=ROOT / 'artifacts'))
NETWORK = RUN / 'network.jsonl'; NETWORK.touch()
CONTROL = RUN / 'control.json'; CONTROL.write_text('{}')
SIGNAL = RUN / 'signal.txt'
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
base = f'http://127.0.0.1:{port}'
env = {**os.environ, 'CRW_DATA_DIR': str(RUN / 'data'), 'CRW_PORT': str(port),
       'CRW_NETWORK_AUDIT': str(NETWORK), 'CRW_DELAY_CONTROL': str(CONTROL),
       'CRW_DELAY_SIGNAL': str(SIGNAL), 'OPENROUTER_API_KEY': 'synthetic-never-transmitted'}
log = (RUN / 'server.log').open('w')
server = subprocess.Popen([sys.executable, 'tests/serve_checked.py'], cwd=ROOT, env=env, stdout=log, stderr=log, start_new_session=True)
try:
    with httpx.Client(base_url=base, timeout=30, trust_env=False) as client:
        for _ in range(150):
            try:
                if client.get('/api/health').status_code == 200: break
            except httpx.HTTPError: pass
            time.sleep(.1)
        else: raise RuntimeError('Server did not start')
        documents, reviews = [], []
        for name, text in [('first.txt', b'Each party liability is limited to fees paid.'), ('second.txt', b'Each party must protect confidential information.')]:
            doc = client.post('/api/documents', files={'file': (name, text)}).raise_for_status().json()
            documents.append(doc)
            reviews.append(client.post(f"/api/documents/{doc['id']}/reviews", json={'playbook_id': 'commercial'}).raise_for_status().json())
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={'width':1440, 'height':1000})
            page.goto(base)
            page.locator(f'.doc-row[data-document-id="{documents[0]["id"]}"]').click()
            expect(page.get_by_role('heading', level=2, name='first.txt')).to_be_visible()
            expect(page.locator('#main')).to_have_attribute('aria-busy', 'false')
            page.get_by_label('Provider', exact=True).fill('Test')
            page.get_by_label('Model', exact=True).fill('invalid!')
            page.get_by_role('checkbox').check()
            CONTROL.write_text(json.dumps({'path': f'/api/reviews/{reviews[0]["id"]}/ai', 'hold': True}))
            page.get_by_role('button', name='Run AI assistance').click()
            for _ in range(1000):
                if SIGNAL.exists() and SIGNAL.read_text() == 'entered': break
                time.sleep(.01)
            else: raise AssertionError('Invalid AI request was not held')
            page.locator(f'.doc-row[data-document-id="{documents[1]["id"]}"]').click()
            expect(page.get_by_role('heading', level=2, name='second.txt')).to_be_visible()
            expect(page.locator('#main')).to_have_attribute('aria-busy', 'false')
            with page.expect_response(lambda r: r.url.endswith(f'/reviews/{reviews[0]["id"]}/ai')) as response:
                CONTROL.write_text('{}')
            assert response.value.status == 422
            # Drain the real failure handler, including its old-review GET.
            page.wait_for_timeout(300)
            with page.expect_download() as download:
                page.get_by_label('Export review').select_option('json')
            download.value.save_as(RUN / 'selected-review.json')
            exported = json.loads((RUN / 'selected-review.json').read_text())
            assert exported['document']['id'] == documents[1]['id'], 'Late AI error restored another document review'
            expect(page.get_by_role('heading', level=2, name='second.txt')).to_be_visible()
            assert not page.get_by_role('checkbox').is_checked()
            assert client.get(f"/api/reviews/{reviews[0]['id']}").json()['ai_status'] == 'NOT_REQUESTED'
            trigger = page.get_by_role('button', name='Edit', exact=True)
            trigger.click()
            dialog = page.get_by_role('dialog', name='Edit playbook')
            expect(dialog).to_be_visible()
            expect(page.get_by_label('Playbook YAML')).to_be_focused()
            dialog.get_by_role('button', name='Save playbook').focus()
            page.keyboard.press('Tab')
            expect(dialog.get_by_role('button', name='Close', exact=True)).to_be_focused()
            page.keyboard.press('Shift+Tab')
            expect(dialog.get_by_role('button', name='Save playbook')).to_be_focused()
            page.get_by_label('Playbook YAML').fill('name: incomplete')
            dialog.get_by_role('button', name='Save playbook').click()
            expect(page.get_by_label('Playbook YAML')).to_have_attribute('aria-invalid', 'true')
            expect(dialog.get_by_role('alert')).to_be_visible()
            page.keyboard.press('Escape')
            expect(dialog).to_have_count(0)
            expect(trigger).to_be_focused()
            browser.close()
        assert NETWORK.read_text() == ''
        result = {'author':'Ethan', 'status':'PASS', 'run':str(RUN.relative_to(ROOT)), 'checks':['held actual invalid AI request','422 before provider invocation','new selection retains its own exported review','consent reset','no backend outbound sockets','modal initial focus, tab containment, escape, focus return and announced field error']}
        (ROOT / 'artifacts/readiness/frontend-state.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result))
finally:
    CONTROL.write_text('{}')
    if server.poll() is None:
        os.killpg(server.pid, signal.SIGTERM); server.wait(timeout=10)
    log.close()
