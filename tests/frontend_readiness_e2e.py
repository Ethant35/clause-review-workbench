"""Real browser checks for onboarding, recovery, and accessible review flow.

Author: Ethan. Uses the real HTTP API, parsers, SQLite storage, and Chromium.
No fake analysis responses, external AI calls, or contract data leaves localhost.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import traceback
from urllib.parse import urlparse
import uuid

import httpx
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
RUN = Path(tempfile.mkdtemp(prefix='frontend-readiness-', dir=ROOT / 'artifacts'))
DATA = RUN / 'data'
NETWORK = RUN / 'network.jsonl'
NETWORK.touch()
DELAY_CONTROL = RUN / 'delay-control.json'
DELAY_CONTROL.write_text('{}')
DELAY_SIGNAL = RUN / 'delay-signal.txt'
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    PORT = sock.getsockname()[1]
BASE = f'http://127.0.0.1:{PORT}'
REGISTRY = Path(os.environ.get('CRW_PROCESS_REGISTRY', ROOT / 'artifacts/processes.json'))
RESULTS = []
SERVER = None
AXE_COPY = ROOT / 'frontend/dist/axe-e2e-only.js'


def passed(name, detail):
    RESULTS.append({'id': name, 'status': 'PASS', 'detail': detail})


def check_axe(page, name):
    page.add_script_tag(url=f'{BASE}/axe-e2e-only.js')
    result = page.evaluate("""async () => {
      const result = await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']}});
      return result.violations.map(v => ({id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.map(n => ({target: n.target, summary: n.failureSummary}))}));
    }""")
    RESULTS.append({'id': name, 'status': 'PASS' if not any(v['impact'] in ('critical', 'serious') for v in result) else 'FAIL', 'violations': result})
    assert not any(v['impact'] in ('critical', 'serious') for v in result), json.dumps(result)


def run():
    global SERVER
    RUN.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.pop('OPENROUTER_API_KEY', None)
    env.update(CRW_DATA_DIR=str(DATA), CRW_PORT=str(PORT), CRW_NETWORK_AUDIT=str(NETWORK),
               CRW_DELAY_CONTROL=str(DELAY_CONTROL), CRW_DELAY_SIGNAL=str(DELAY_SIGNAL))
    log = (RUN / 'server.log').open('w')
    shutil.copyfile(ROOT / 'frontend/node_modules/axe-core/axe.min.js', AXE_COPY)
    SERVER = subprocess.Popen([sys.executable, 'tests/serve_checked.py'], cwd=ROOT, env=env,
                              stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    REGISTRY.parent.mkdir(exist_ok=True)
    REGISTRY.write_text(json.dumps([os.getpgrp(), SERVER.pid]))
    client = httpx.Client(base_url=BASE, timeout=40, trust_env=False)
    try:
        for _ in range(150):
            try:
                if client.get('/api/health').status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(.1)
        else:
            raise RuntimeError('Local application API did not start: ' + (RUN / 'server.log').read_text()[-2000:])

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            context = browser.new_context(viewport={'width': 1440, 'height': 1000})
            page = context.new_page()
            external = []
            page.on('request', lambda request: external.append(request.url) if urlparse(request.url).hostname not in {'127.0.0.1', 'localhost', None} else None)
            page.goto(BASE)
            expect(page.get_by_role('heading', name='Start a contract review')).to_be_visible()
            page.keyboard.press('Tab')
            expect(page.get_by_role('link', name='Skip to main content')).to_be_focused()
            page.keyboard.press('Enter')
            expect(page.locator('#main')).to_be_focused()
            page.screenshot(path=str(RUN / 'onboarding-desktop.png'), full_page=True)
            passed('fresh-onboarding-and-skip-link', 'Fresh profile shows the local-review guide; keyboard skip link moves to main content.')
            check_axe(page, 'axe-first-run')

            page.get_by_role('button', name='Skip for now').click()
            expect(page.get_by_role('heading', name='Start a contract review')).to_have_count(0)
            assert page.evaluate("localStorage.getItem('clause-workbench:onboarding:v1')") == 'dismissed'
            assert list(page.evaluate('Object.keys(localStorage)')) == ['clause-workbench:onboarding:v1']
            page.reload()
            expect(page.get_by_role('heading', name='Start a contract review')).to_have_count(0)
            page.get_by_role('button', name='Getting started').click()
            expect(page.get_by_role('heading', name='Start a contract review')).to_be_visible()
            passed('skip-persists-and-guide-replays', 'Skip persists across reload; the footer action reopens onboarding.')

            page.get_by_role('button', name='Use synthetic sample').click()
            expect(page.get_by_role('heading', name='Your contract is ready')).to_be_visible(timeout=15000)
            expect(page.get_by_role('heading', level=2, name='synthetic-sample.txt')).to_be_visible()
            page.get_by_role('button', name='Run local review').click()
            expect(page.get_by_text('Review complete.', exact=True)).to_be_visible(timeout=20000)
            expect(page.locator('.issue-card').first).to_be_visible()
            passed('synthetic-sample-real-review', 'The clearly labeled synthetic text was sent only to the local upload API and produced a real configured-playbook review; no output was fabricated.')

            page.get_by_label('Choose a contract to upload').set_input_files({
                'name': 'onboarding-sample.txt', 'mimeType': 'text/plain',
                'buffer': b'Each party will maintain confidential information in confidence and use it only to perform this agreement.\n\nEach party\'s aggregate liability arising out of this agreement will not exceed fees paid in the twelve months before the event giving rise to liability.'
            })
            expect(page.get_by_role('heading', level=2, name='onboarding-sample.txt')).to_be_visible(timeout=15000)
            page.get_by_role('button', name='Run review').first.click()
            expect(page.get_by_text('Review complete.', exact=True)).to_be_visible(timeout=20000)
            expect(page.get_by_role('tab', name='Findings')).to_be_visible()
            expect(page.locator('.issue-card').first).to_be_visible()
            findings_tab = page.get_by_role('tab', name='Findings')
            findings_tab.focus()
            page.keyboard.press('ArrowRight')
            expect(page.get_by_role('tab', name='Rule checks')).to_have_attribute('aria-selected', 'true')
            page.keyboard.press('ArrowRight')
            expect(page.get_by_role('tab', name='Extracted source')).to_have_attribute('aria-selected', 'true')
            page.keyboard.press('ArrowLeft')
            expect(page.get_by_role('tab', name='Rule checks')).to_have_attribute('aria-selected', 'true')
            page.get_by_role('tab', name='Findings').click()
            passed('first-useful-result', 'Uploaded a real text contract, ran the local configured playbook, and inspected actual findings.')
            page.screenshot(path=str(RUN / 'review-desktop.png'), full_page=True)
            check_axe(page, 'axe-review-results')

            # Delay a real local document response to prove an older selection cannot win.
            records = client.get('/api/documents?limit=100&offset=0').raise_for_status().json()
            onboarding_doc = next(item for item in records if item['name'] == 'onboarding-sample.txt')
            sample_doc = next(item for item in records if item['name'] == 'synthetic-sample.txt')
            page.get_by_role('button', name='Refresh workspace').click()
            sample_row = page.locator(f'.doc-row[data-document-id="{sample_doc["id"]}"]')
            expect(sample_row).to_be_visible(timeout=10000)
            sample_row.click()
            expect(page.get_by_role('heading', level=2, name='synthetic-sample.txt')).to_be_visible()
            DELAY_SIGNAL.unlink(missing_ok=True)
            DELAY_CONTROL.write_text(json.dumps({'document_id': onboarding_doc['id'], 'hold': True}))
            page.locator(f'.doc-row[data-document-id="{onboarding_doc["id"]}"]').click()
            for _ in range(1000):
                if DELAY_SIGNAL.exists() and DELAY_SIGNAL.read_text() == 'entered':
                    break
                time.sleep(.01)
            else:
                raise AssertionError('The test server did not hold the requested real document response.')
            sample_row.click()
            expect(page.locator('#main')).to_have_attribute('aria-busy', 'false', timeout=10000)
            DELAY_CONTROL.write_text(json.dumps({'document_id': onboarding_doc['id'], 'hold': False}))
            for _ in range(1000):
                if DELAY_SIGNAL.exists() and DELAY_SIGNAL.read_text() == 'released':
                    break
                time.sleep(.01)
            else:
                raise AssertionError('The held real document response did not resume.')
            expect(page.get_by_role('heading', level=2, name='synthetic-sample.txt')).to_be_visible()
            expect(sample_row).to_have_class('doc-row selected')
            passed('stale-document-response-guard', 'A delayed real local document response arrived after a newer selection; the newer selected document remained visible.')

            page.set_viewport_size({'width': 390, 'height': 844})
            overflow = page.evaluate('''() => ({width: document.documentElement.scrollWidth, offenders: [...document.querySelectorAll("body *")].map(el => ({tag:el.tagName, className:String(el.className||""), text:(el.innerText||"").slice(0,80), right:Math.round(el.getBoundingClientRect().right)})).filter(x => x.right > innerWidth + 1).slice(0,12)})''')
            assert overflow['width'] <= 390, f'Mobile viewport has horizontal overflow: {overflow}'
            expect(page.get_by_role('tab', name='Findings')).to_be_visible()
            check_axe(page, 'axe-narrow-review')
            page.screenshot(path=str(RUN / 'review-mobile.png'), full_page=True)
            passed('narrow-review-layout', 'At 390 px, findings remain visible and document width does not overflow the viewport.')
            page.set_viewport_size({'width': 720, 'height': 900})
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), '200% reflow viewport has horizontal overflow.'
            page.set_viewport_size({'width': 390, 'height': 844})

            page.context.set_offline(True)
            page.get_by_role('button', name='Refresh workspace').click()
            expect(page.get_by_role('alert').first).to_be_visible()
            page.context.set_offline(False)
            page.get_by_role('button', name='Refresh workspace').click()
            expect(page.get_by_role('alert')).to_have_count(0)
            passed('network-error-recovery', 'A failed refresh shows an inline alert; retrying after connectivity returns clears the error.')

            # Fill a genuine local library/history so both 50-row UI continuations run.
            original_doc = client.get('/api/documents?limit=100&offset=0').raise_for_status().json()[0]
            books = client.get('/api/playbooks').raise_for_status().json()
            playbook_id = books[0]['id']
            for index in range(51):
                response = client.post('/api/documents', files={'file': (f'pagination-{index:02}.txt', b'Pagination fixture contract text.', 'text/plain')})
                response.raise_for_status()
            for _ in range(50):
                response = client.post(f"/api/documents/{original_doc['id']}/reviews", json={'playbook_id': playbook_id})
                response.raise_for_status()
            summary_page = client.get(f"/api/documents/{original_doc['id']}/reviews?summary=true&limit=50&offset=0").raise_for_status().json()
            assert len(summary_page) == 50
            assert {'id', 'document_id', 'playbook_id', 'playbook_name', 'created_at', 'ai_status'} <= summary_page[0].keys()
            assert {'extraction_revision', 'review_revision'} <= summary_page[0].keys()
            assert not {'issues', 'checks', 'playbook_snapshot', 'ai_audit', 'ai_error'} & summary_page[0].keys()
            assert len(client.get(f"/api/documents/{original_doc['id']}/reviews?summary=true&limit=50&offset=50").raise_for_status().json()) == 1
            page.get_by_role('button', name='Refresh workspace').click()
            expect(page.get_by_role('button', name='Load more documents')).to_be_visible(timeout=10000)
            page.get_by_role('button', name='Load more documents').click()
            expect(page.get_by_text('53 total')).to_be_visible(timeout=10000)
            page.get_by_role('button', name='pagination-50.txt').click()
            page.get_by_role('button', name=original_doc['name']).click()
            expect(page.get_by_text('50+ reviews loaded')).to_be_visible(timeout=10000)
            page.get_by_role('button', name='Load more reviews').click()
            expect(page.get_by_text('51 saved reviews')).to_be_visible(timeout=10000)
            passed('bounded-document-and-review-pagination', 'Loaded the second document and review-summary pages from real local API records. Summaries contain metadata and revision flags but omit issue, check, playbook-snapshot, and AI-detail payloads.')

            page.get_by_role('button', name='Getting started').click()
            expect(page.get_by_role('heading', name='Review a finding and record your decision')).to_be_visible()
            page.get_by_role('button', name='Skip for now').click()
            expect(page.get_by_role('heading', name='Review a finding and record your decision')).to_have_count(0)
            passed('guide-replays-after-first-success', 'The returning-user guide replays with review-specific guidance and can be dismissed again.')

            # Return to a blank client-only profile while retaining the server-side real review.
            page.reload()
            expect(page.get_by_role('heading', name='Review a finding and record your decision')).to_have_count(0)
            passed('returning-user-does-not-repeat-first-run', 'Existing saved review opens without forcing the first-run guide.')
            assert not external, 'Browser requested a non-local origin: ' + ', '.join(external)
            browser.close()
        assert NETWORK.read_text() == '', 'Backend made an outbound socket connection.'
        passed('no-external-transmission', 'Browser requests and audited backend sockets stayed on localhost; AI was not configured or invoked.')
    except Exception as exc:
        RESULTS.append({'id': 'run-error', 'status': 'FAIL', 'detail': str(exc), 'trace': traceback.format_exc()})
        raise
    finally:
        if SERVER and SERVER.poll() is None:
            os.killpg(SERVER.pid, signal.SIGTERM)
            SERVER.wait(timeout=10)
        REGISTRY.write_text(json.dumps([os.getpgrp()]))
        AXE_COPY.unlink(missing_ok=True)
        log.close()
        report = {'author': 'Ethan', 'created_at': datetime.now(timezone.utc).isoformat(),
                  'run': str(RUN.relative_to(ROOT)), 'results': RESULTS,
                  'passed': sum(item['status'] == 'PASS' for item in RESULTS),
                  'failed': sum(item['status'] == 'FAIL' for item in RESULTS)}
        (RUN / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'run': str(RUN.relative_to(ROOT)), 'passed': report['passed'], 'failed': report['failed']}))
    return report['failed'] == 0


if __name__ == '__main__':
    raise SystemExit(0 if run() else 1)
