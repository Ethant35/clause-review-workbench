"""Author: Ethan. Import a prior release's data into the bundled runtime."""
import argparse
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
from io import BytesIO

import httpx

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('app',type=Path)
parser.add_argument('--baseline', choices=('v1.2.0','v1.3.0','v1.4.0'), default='v1.2.0',
                    help='release to create the original review with (default: v1.2.0)')
args=parser.parse_args()
baseline_ref={'v1.2.0':'v1.2.0',
              # v1.3.0's release commit is present in this checkout, but its
              # local tag ref is not. Pin the verified release commit so the
              # update test does not require a network fetch.
              'v1.3.0':'e1fa5dcad0e1e5be0571f755006fa0abc6c6b19b',
              'v1.4.0':'03b6dbaed1fac5bc2cad833a20be0770d7bcf895'}[args.baseline]
work=Path(tempfile.mkdtemp(prefix='native-upgrade-',dir=ROOT/'artifacts'))
old=work/args.baseline;old.mkdir()
with tarfile.open(fileobj=BytesIO(subprocess.check_output(['git','archive',baseline_ref],cwd=ROOT))) as archive:archive.extractall(old,filter='data')
data=work/'old-data'
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
env=os.environ.copy();env.pop('OPENROUTER_API_KEY',None);env.update(CRW_DATA_DIR=str(data),CRW_PORT=str(port))
p=None
checks=[]

def start(command,cwd,environment):
    global p
    p=subprocess.Popen(command,cwd=cwd,env=environment,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
    for _ in range(150):
        if p.poll() is not None:raise RuntimeError('server exited')
        try:
            if client.get('/api/health').status_code==200:return
        except httpx.HTTPError:pass
        time.sleep(.1)
    raise RuntimeError('server did not start')

def stop():
    global p
    if p and p.poll() is None:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=20)
    p=None

def stored_review(database, review_id):
    with sqlite3.connect(database) as connection:
        row=connection.execute('SELECT data FROM reviews WHERE id=?',(review_id,)).fetchone()
    assert row is not None, f'missing stored review {review_id}'
    return row[0]

try:
    with httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=30,trust_env=False) as client:
        start([sys.executable,'-m','backend.workbench.launcher'],old,env) if (old/'frontend/dist/index.html').exists() else start([sys.executable,'-m','uvicorn','backend.workbench.main:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],old,env)
        baseline_health=client.get('/api/health').raise_for_status().json()
        source=b'Provider shall indemnify Customer for all claims without limit.\n'
        doc=client.post('/api/documents',files={'file':('prior.txt',source)}).raise_for_status().json()
        review=client.post(f'/api/documents/{doc["id"]}/reviews',json={'playbook_id':'commercial'}).raise_for_status().json()
        issue=review['issues'][0]
        client.patch(f'/api/reviews/{review["id"]}/issues/{issue["id"]}',json={'status':'accepted','notes':'Preserve the previous reviewer decision.'}).raise_for_status()
        saved_review=client.get(f'/api/reviews/{review["id"]}').raise_for_status().json()
        assert saved_review['issues'][0]['status']=='accepted'
        original_review_json=stored_review(data/'workbench.sqlite3',review['id'])
        before=(data/'workbench.sqlite3').read_bytes(); stop()
        checks.append(f'{args.baseline} created original, review, decision and note')
        app=args.app.resolve();resources=app/'Contents/Resources';runtime=resources/'python/bin/python3';bootstrap=resources/'bootstrap.py'
        clean={'PATH':'/usr/bin:/bin','HOME':str(Path.home()),'PYTHONDONTWRITEBYTECODE':'1'}
        backup=work/'import-backup';newdata=work/'imported-data'
        for command in (['backup',str(data),str(backup)],['restore',str(backup),str(newdata)]):
            result=subprocess.run([str(runtime),'-s','-B',str(bootstrap),'recover',*command],env=clean,capture_output=True,text=True,timeout=30)
            assert result.returncode==0,result.stdout+result.stderr
        assert (data/'workbench.sqlite3').read_bytes()==before
        checks.append('bundled recovery imports into a separate folder without changing old database')
        clean.update(CRW_DATA_DIR=str(newdata),CRW_PORT=str(port))
        start([str(runtime),'-s','-B',str(bootstrap),'serve'],resources/'workbench',clean)
        historical=client.get(f'/api/reviews/{review["id"]}').raise_for_status().json()
        imported_review_json=stored_review(newdata/'workbench.sqlite3',review['id'])
        assert imported_review_json==original_review_json
        assert historical['verification_status']=='HISTORICAL_UNVERIFIED'
        assert historical['issues'][0]['status']=='accepted'
        assert historical['issues'][0]['notes']=='Preserve the previous reviewer decision.'
        assert historical['playbook_snapshot']==saved_review['playbook_snapshot']
        assert historical['review_revision']==saved_review['review_revision']
        assert historical['extraction_revision']==saved_review['extraction_revision']
        assert client.get(f'/api/documents/{doc["id"]}/original').content==source
        extraction_is_stale=(baseline_health['extraction_revision'] != client.get('/api/health').json()['extraction_revision'])
        rerun_response=client.post(f'/api/documents/{doc["id"]}/reviews',json={'playbook_id':'commercial'})
        assert rerun_response.status_code == (409 if extraction_is_stale else 201), (rerun_response.status_code, baseline_health)
        if not extraction_is_stale:
            same_document_review=rerun_response.json()
            assert same_document_review['id']!=review['id']
            assert all(issue['status']=='unresolved' and not issue['notes'] for issue in same_document_review['issues'])
        checks.append('history, original, saved policy, decision and note remain; review gate follows extraction revision')
        fresh=client.post(f'/api/documents/{doc["id"]}/reprocess').raise_for_status().json()
        assert fresh['id']!=doc['id'] and fresh['source_document_id']==doc['id']
        assert client.get(f'/api/documents/{fresh["id"]}/reviews').json()==[]
        newreview=client.post(f'/api/documents/{fresh["id"]}/reviews',json={'playbook_id':'commercial'}).raise_for_status().json()
        assert newreview['verification_status']=='CURRENT_CHECKS'
        assert all(i['status']=='unresolved' and not i['notes'] for i in newreview['issues'])
        assert 'Preserve the previous reviewer decision.' in client.get(f'/api/reviews/{review["id"]}/export').text
        assert client.get(f'/api/reviews/{newreview["id"]}/export').status_code==200
        checks.append('explicit reprocess creates new results without copying or erasing old decisions')
        stop()
        result={'author':'Ethan','status':'PASS','baseline':args.baseline,'baseline_ref':baseline_ref,'checks':checks,'work_directory':str(work)}
        (work/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
finally:stop()
