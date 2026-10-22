"""Verify the built archive from a fresh extraction and fresh database."""
from pathlib import Path
import json
import os
import signal
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import httpx
from playwright.sync_api import sync_playwright, expect
root=Path(__file__).resolve().parents[1]
archive=Path(sys.argv[1]).resolve()
out=root/'artifacts'
target=Path(tempfile.mkdtemp(prefix='crw-deployment-'))
with tarfile.open(archive) as tar: tar.extractall(target,filter='data')
project=target/'clause-review-workbench-1.0.0'
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
env=os.environ.copy();env.pop('OPENROUTER_API_KEY',None);env.update(CRW_PORT=str(port))
log=(out/'package-deployment.log').open('w')
p=subprocess.Popen(['bash','scripts/start.sh'],cwd=project,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(out/'processes.json').write_text(json.dumps([os.getpgrp(),p.pid]))
try:
    with httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=30,trust_env=False) as c:
        for _ in range(600):
            try:
                if c.get('/api/health').status_code==200:break
            except httpx.HTTPError:pass
            if p.poll() is not None:raise RuntimeError('Deployment process exited')
            time.sleep(.1)
        else:raise RuntimeError('Deployment did not start')
        assert c.get('/api/documents').json()==[]
        with sync_playwright() as pw:
            browser=pw.chromium.launch();page=browser.new_page();page.goto(f'http://127.0.0.1:{port}')
            expect(page.get_by_role('heading',name='Document library')).to_be_visible()
            page.locator('.upload-box input').set_input_files(root/'corpus/contracts/04-renewal-and-unilateral-audit.txt')
            expect(page.get_by_role('heading',level=2,name='04-renewal-and-unilateral-audit.txt')).to_be_visible()
            page.get_by_role('button',name='Run review',exact=True).click();expect(page.locator('.issue-card')).to_have_count(2)
            page.locator('.issue-card').first.click();page.get_by_role('button',name='Accept',exact=True).click();expect(page.locator('.issue-card').first.locator('.issue-status')).to_have_text('accepted')
            with page.expect_download() as d:page.get_by_label('Export review').select_option('json')
            d.value.save_as(out/'package-export.json');report=json.loads((out/'package-export.json').read_text());assert any(i['status']=='accepted' for i in report['issues'])
            browser.close()
    (out/'package-result.json').write_text(json.dumps({'status':'PASS','archive':archive.name,'fresh_extraction':str(target),'checks':['production startup','fresh database','browser upload','two expected findings','reviewer decision','JSON export'],'author':'Ethan'},indent=2)+'\n')
finally:
    if p.poll() is None:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=10)
    log.close();(out/'processes.json').write_text('[]')
