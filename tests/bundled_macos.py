"""Author: Ethan. Exercise a relocated self-contained app without developer PATH."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import tempfile
import time
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]

def request(port, path, payload=None, method=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}',data=data,method=method,headers={'Content-Type':'application/json'} if data else {})
    with urllib.request.urlopen(req,timeout=10) as response:
        return response.read()

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('app',type=Path); parser.add_argument('--report',type=Path,required=True); args=parser.parse_args()
    work = Path(tempfile.mkdtemp(prefix='bundle-journey-', dir=ROOT/'artifacts'))
    app = work/'Applications'/'Clause Review Workbench.app'; app.parent.mkdir()
    shutil.copytree(args.app,app,symlinks=True)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
    support = work/'support'; data = support/'Data'
    env={'PATH':'/usr/bin:/bin','HOME':str(Path.home()),'CRW_HEADLESS':'1','CRW_NO_OPEN':'1','CRW_APP_SUPPORT':str(support),'CRW_DATA_DIR':str(data),'CRW_PORT':str(port)}
    checks=[]; native=None
    def launch():
        p = subprocess.Popen([str(app/'Contents/MacOS/Workbench')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(120):
            if p.poll() is not None: raise RuntimeError('Native launcher exited')
            try:
                request(port,'/api/health'); return p
            except (OSError,urllib.error.URLError):time.sleep(.25)
        p.terminate();p.wait(timeout=5);raise RuntimeError('Bundle did not start')
    def stop(p):
        p.terminate();p.wait(timeout=5)
        for _ in range(80):
            try:request(port,'/api/health');time.sleep(.25)
            except (OSError,urllib.error.URLError): return
        raise RuntimeError('Server survived launcher exit')
    try:
        native=launch();checks.append('relocated app starts with only system PATH; no Python/uv/Node setup')
        page=request(port,'/').decode(); assert '<div id="root">' in page;checks.append('bundled frontend is served')
        playbooks=json.loads(request(port,'/api/playbooks'));assert playbooks
        boundary='bundle-test-boundary'
        contract=(ROOT/'corpus/contracts/06-uncapped-indemnity.txt').read_bytes()
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="services.txt"\r\nContent-Type: text/plain\r\n\r\n'.encode()+contract+f'\r\n--{boundary}--\r\n'.encode())
        req=urllib.request.Request(f'http://127.0.0.1:{port}/api/documents',data=body,headers={'Content-Type':f'multipart/form-data; boundary={boundary}'})
        with urllib.request.urlopen(req) as response:doc=json.load(response)
        rev=json.loads(request(port,f'/api/documents/{doc["id"]}/reviews',{'playbook_id':playbooks[0]['id']}));assert rev['issues']
        issue=rev['issues'][0]
        request(port,f'/api/reviews/{rev["id"]}/issues/{issue["id"]}',{'status':'accepted','notes':'Bundled installation test note'},'PATCH')
        exported=json.loads(request(port,f'/api/reviews/{rev["id"]}/export'))
        assert 'Bundled installation test note' in json.dumps(exported)
        assert request(port,f'/api/documents/{doc["id"]}/original') == contract
        checks.append('upload, actual review, original source, saved finding decision and export')
        stop(native);native=None;checks.append('launcher exit stops its own server')
        native=launch()
        restored=json.loads(request(port,f'/api/reviews/{rev["id"]}'))
        assert restored['issues'][0]['notes']=='Bundled installation test note'
        checks.append('returning launch preserves original review and decision')
        stop(native);native=None
        resources=app/'Contents/Resources';runtime=resources/'python/bin/python3';bootstrap=resources/'bootstrap.py'
        backup=work/'backup';restore=work/'restored'
        for command in (['doctor',str(data)],['backup',str(data),str(backup)],['restore',str(backup),str(restore)],['doctor',str(restore)]):
            result=subprocess.run([str(runtime),'-s','-B',str(bootstrap),'recover',*command],env=env,capture_output=True,text=True,timeout=30)
            assert result.returncode==0,result.stdout+result.stderr
        assert (restore/'sources'/doc['id']).read_bytes()==contract
        checks.append('bundled offline doctor, backup, new-destination restore and source verification')
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps({'author':'Ethan','status':'PASS','checks':checks,'work_directory':str(work),'limits':['Local automated test, not an unfamiliar-user study','Does not establish Apple notarization or downloaded Gatekeeper acceptance']},indent=2)+'\n')
        print(json.dumps({'status':'PASS','checks':len(checks),'report':str(args.report)}))
    finally:
        if native and native.poll() is None:stop(native)

if __name__=='__main__':main()
