"""Bounded regression controls from the exposed CUAD diagnostic. Author: Ethan."""
from pathlib import Path
import json
import yaml
from fastapi.testclient import TestClient
from backend.workbench.engine import analyze, validate_evidence
from backend.workbench.models import Playbook
from backend.workbench.parsing import extract
from backend.workbench import store
from backend.workbench.main import app, save_playbook

ROOT=Path(__file__).parents[1]
def policy(): return Playbook.model_validate(yaml.safe_load((ROOT/'playbooks/commercial.yaml').read_text()))

def test_operating_fee_cap_and_without_cause_right_are_located_with_exact_evidence():
    # Adapted wording, not a held-out test or a lawyer-authored risk judgment.
    text="Supplier's liability for damages to Customer for any cause whatsoever, regardless of the form of action, and whether in contract or tort, including negligence, shall be limited to one month's fees and prepaid fees.\nEither party may terminate this Agreement without cause at any time effective upon thirty (30) days' written notice."
    document=extract(text.encode());issues,checks=analyze(document,policy())
    for rid in ['liability-cap']:
        found=[i for i in issues if i['rule_id']==rid]
        assert found and all(not i['absence'] and validate_evidence(i,document) for i in found)
        assert next(c for c in checks if c['rule_id']==rid)['outcome']=='NEEDS_REVIEW'
    # This sentence expressly meets the configured mutual 30-day condition.
    # A configured match creates no issue; it is not a legal-approval judgment.
    assert next(c for c in checks if c['rule_id']=='termination-convenience')['outcome']=='COMPLIANT'
    assert not any(i['rule_id']=='termination-convenience' for i in issues)

def test_service_limits_and_cause_only_termination_do_not_supply_the_missing_rules():
    document=extract(b'Services are limited to one hour per month.\nEither party may terminate for material breach after thirty days to cure.')
    issues,_=analyze(document,policy())
    assert all(next(i for i in issues if i['rule_id']==rid)['absence'] for rid in ['liability-cap','termination-convenience'])

def test_no_cause_negation_is_not_an_acceptable_termination_right():
    doc=extract(b'Neither party may terminate without cause. Either party must give 30 days notice of breach.')
    issues,checks=analyze(doc,policy())
    assert next(c for c in checks if c['rule_id']=='termination-convenience')['outcome']=='NEEDS_REVIEW'
    assert next(i for i in issues if i['rule_id']=='termination-convenience')['confidence']=='NEEDS_REVIEW'

def test_corrected_policy_is_added_without_rewriting_saved_policy(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path);monkeypatch.setattr(store,'RETENTION_DAYS',0)
    store.initialize();old=yaml.safe_load((ROOT/'playbooks/commercial.yaml').read_text());old['version']='1.0.0';old['name']='Existing reviewer policy'
    save_playbook('commercial',yaml.safe_dump(old))
    original=json.dumps(store.get('playbooks','commercial'),sort_keys=True)
    with TestClient(app,base_url='http://127.0.0.1') as client:
        assert json.dumps(client.get('/api/playbooks/commercial').json(),sort_keys=True)==original
        assert client.get('/api/playbooks/commercial-1.0.1').json()['version']=='1.0.1'


def test_headings_and_breach_notice_cannot_supply_a_convenience_right():
    doc=extract(b'Headings are for convenience only. Either party may terminate for material breach on 30 days notice.')
    _,checks=analyze(doc,policy())
    assert next(c for c in checks if c['rule_id']=='termination-convenience')['outcome']=='NEEDS_REVIEW'
