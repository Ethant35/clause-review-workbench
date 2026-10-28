"""Author: Ethan. The UI sample teaches source-linked review, not rule suppression."""
from pathlib import Path

import yaml

from workbench.engine import analyze, validate_evidence
from workbench.models import Playbook
from workbench.parsing import extract

ROOT = Path(__file__).resolve().parents[1]


def test_full_sample_preserves_screening_and_exposes_exception_and_cost():
    source = (ROOT / "frontend/src/sample.ts").read_text().split("`")[1]
    document = extract(source.encode())
    policy = Playbook.model_validate(yaml.safe_load((ROOT / "playbooks/commercial.yaml").read_text()))
    issues, checks = analyze(document, policy)
    assert len(checks) == len(policy.rules)
    assert all(validate_evidence(issue, document) for issue in issues)
    assert not any(issue["absence"] for issue in issues)
    by_rule = {issue["rule_id"]: issue for issue in issues}
    assert {"unilateral-amendment", "liability-cap", "termination-convenience"} <= by_rule.keys()
    assert by_rule["unilateral-amendment"]["confidence"] == "OBJECTIVE"
    cap = by_rule["liability-cap"]
    assert cap["confidence"] == "NEEDS_REVIEW"
    cap_links = [link for link in cap["interactions"] if link["kind"] == "cap-exception"]
    assert any(link["separate_limit_located"] for link in cap_links)
    assert any("twice the fees" in anchor["text"] for link in cap_links for anchor in link["evidence"])
    cost = by_rule["termination-convenience"]
    assert any(link["kind"] == "termination-cost" for link in cost["interactions"])
    assert "remaining fees" in " ".join(anchor["text"] for link in cost["interactions"] for anchor in link["evidence"])
