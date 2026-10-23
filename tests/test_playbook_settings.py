"""Author: Ethan. Real settings transactions preserve matching and prior reviews."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from backend.workbench import store
from backend.workbench.main import app, save_playbook, parse_playbook

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DATA', tmp_path)
    store.initialize()
    text = next(Path('playbooks').glob('*.yaml')).read_text()
    save_playbook('example', text)
    return TestClient(app, base_url='http://127.0.0.1')

def test_partial_settings_preserve_patterns_and_other_rules(client):
    before = parse_playbook(store.get('playbooks', 'example')['yaml']).model_dump()
    view = client.get('/api/playbooks/example/settings').json()
    rule = view['rules'][0]
    response = client.patch('/api/playbooks/example/settings', json={'revision':view['revision'], 'name':'My positions', 'rules':[{'id':rule['id'],'severity':'low','required':False,'fallback_language':None}]})
    assert response.status_code == 200, response.text
    after = parse_playbook(store.get('playbooks', 'example')['yaml']).model_dump()
    assert after['name'] == 'My positions'
    assert after['rules'][0]['severity'] == 'low'
    assert after['rules'][0]['required'] is False
    assert after['rules'][0]['fallback_language'] is None
    for key in ('presence','acceptable_all','unacceptable_any'):
        assert before['rules'][0][key] == after['rules'][0][key]
    assert before['rules'][1:] == after['rules'][1:]
    assert response.json()['revision'] != view['revision']
    stale = client.patch('/api/playbooks/example/settings', json={'revision':view['revision'],'name':'Lost edit'})
    assert stale.status_code == 409
    assert store.get('playbooks','example')['name'] == 'My positions'

def test_invalid_settings_are_atomic(client):
    before = store.get('playbooks','example')
    view = client.get('/api/playbooks/example/settings').json()
    rid = view['rules'][0]['id']
    for changes in ({'name':None}, {'rules':[{'id':'unknown','severity':'high'}]}, {'rules':[{'id':rid,'severity':'medium'},{'id':rid,'required':True}]}, {'rules':[{'id':rid,'required':None}]}, {'rules':[{'id':rid,'presence':['.*']}]}, {}):
        response = client.patch('/api/playbooks/example/settings',json={'revision':view['revision'],**changes})
        assert response.status_code == 422, response.text
        assert store.get('playbooks','example') == before
    assert client.get('/api/playbooks/missing/settings').status_code == 404
