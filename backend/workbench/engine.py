"""Conservative condition evaluation with validated source spans."""
import uuid
import time
from contextvars import ContextVar
DEADLINE = ContextVar("review_deadline", default=float("inf"))
import regex
from .models import Playbook

def normalized(text):
    text = text.replace("’", "'").replace("–", "-").replace("\n", " ")
    for word, number in {"twelve":"12", "thirty":"30", "sixty":"60", "ninety":"90"}.items():
        text = regex.sub(r"\b" + word + r"\b", number, text, flags=regex.I)
    return text

def matches(pattern, text):
    if time.monotonic() > DEADLINE.get():
        raise TimeoutError("Analysis time limit")
    text = normalized(text)
    return bool(regex.search(pattern, text, regex.I | regex.S, timeout=0.025))

def any_match(patterns, text):
    return any(matches(p, text) for p in patterns)

def validate_evidence(issue, document):
    if issue["absence"]:
        return issue["source_anchor"] is None and issue["observed_language"] is None
    anchor = issue["source_anchor"]
    if not anchor:
        return False
    block = next((b for b in document["blocks"] if b["id"] == anchor["id"]), None)
    return bool(block and anchor == block and document["text"][block["start"]:block["end"]] == block["text"] and issue["observed_language"] and issue["observed_language"] in block["text"])

def make_issue(rule, block, explanation, confidence="OBJECTIVE"):
    return dict(id=str(uuid.uuid4()), rule_id=rule.id, severity=rule.severity, category=rule.category,
                observed_language=block["text"] if block else None, absence=block is None,
                source_anchor=block, explanation=explanation, preferred_position=rule.preferred_position,
                negotiating_response=rule.negotiation_guidance, status="unresolved", notes="",
                confidence=confidence, origin="deterministic")

def analyze(document, playbook: Playbook):
    DEADLINE.set(time.monotonic() + 5)
    issues, checks = [], []
    for rule in playbook.rules:
        blocks = [b for b in document["blocks"] if any_match(rule.presence, b["text"])]
        props = {}
        outcome = "NOT_APPLICABLE"
        if not blocks and rule.required:
            outcome = "ISSUE"
            issues.append(make_issue(rule, None, "No provision matching this required rule was located in extracted text. This is an absence-based finding; verify the complete original and cross-references.", "NEEDS_REVIEW"))
        elif blocks:
            bad = next((b for b in blocks if any_match(rule.unacceptable_any, b["text"])), None)
            # Every relevant substantive block must meet conditions, or remain uncertain.
            # Standalone headings supply section labels but are not asserted compliant.
            substantive = [b for b in blocks if b["kind"] != "heading"] or blocks
            good = [b for b in substantive if all(any_match(group, b["text"]) for group in rule.acceptable_all)]
            if rule.id == "liability-cap":
                cap = next((b for b in substantive if matches(r"(?:capped|not exceed|limited to).{0,100}(?:the )?fees (?:paid|payable)", b["text"])), None)
                props = {"explicit_fee_cap": bool(cap), "basis": "fees paid/payable" if cap else "unresolved", "period_months": None}
                if cap:
                    period = regex.search(r"(?:preceding|prior|previous|last)\s+(\d+)\s+months|(?P<before>\d+)\s+months before", normalized(cap["text"]), regex.I)
                    props["period_months"] = int(period[1] or period["before"]) if period else None
            if bad:
                outcome = "ISSUE"
                explanation = "The quoted provision matches a configured unacceptable condition. Compare the full agreement and rule guidance before deciding."
                if good:
                    explanation += " Conflicting acceptable language also exists; the conflict requires reviewer resolution."
                issues.append(make_issue(rule, bad, explanation))
            elif len(good) == len(substantive):
                outcome = "COMPLIANT"
            else:
                outcome = "NEEDS_REVIEW"
                unknown = next((b for b in substantive if b not in good), substantive[0])
                issues.append(make_issue(rule, unknown, "Relevant language was found, but the configured conditions do not establish an acceptable or expressly unacceptable position. Context, scope, exceptions, and cross-references require human review.", "NEEDS_REVIEW"))
        checks.append(dict(rule_id=rule.id, category=rule.category, outcome=outcome, properties=props))
    if not all(validate_evidence(i, document) for i in issues):
        raise ValueError("Evidence validation failed")
    return issues, checks
