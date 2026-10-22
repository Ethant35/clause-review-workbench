"""Conservative condition evaluation with validated source spans."""
import uuid
import time
from contextvars import ContextVar
DEADLINE = ContextVar("review_deadline", default=float("inf"))
import regex
from .models import Playbook
from .relations import analyze_relations
from .safety import context_reason, assignment_prohibition, renewal_supported

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
    for relation in issue.get("interactions", []):
        for anchor in relation["evidence"]:
            if anchor not in document["blocks"] or document["text"][anchor["start"]:anchor["end"]] != anchor["text"]:
                return False
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
        if rule.id == "liability-cap":
            # Do not mistake a cap for absence when an exception shares its block.
            blocks = [b for b in document["blocks"] if any_match(rule.presence, b["text"]) or
                      matches(r"(?:aggregate|total|overall) liability.{0,160}(?:cap|limit|exceed)", b["text"])]
        props = {}
        outcome = "NOT_APPLICABLE"
        if not blocks and rule.required:
            outcome = "ISSUE"
            issues.append(make_issue(rule, None, "No provision matching this required rule was located in extracted text. This is an absence-based finding; verify the complete original and cross-references.", "NEEDS_REVIEW"))
        elif blocks:
            bad_blocks = [b for b in blocks if any_match(rule.unacceptable_any, b["text"])
                          and not (rule.id == "assignment" and assignment_prohibition(normalized(b["text"])))]
            bad = next(iter(bad_blocks), None)
            contexts = [(b, context_reason(rule.id, normalized(b["text"]), adverse_match=b in bad_blocks)) for b in blocks]
            contextual = next(((b, reason) for b, reason in contexts if reason), None)
            # Every relevant substantive block must meet conditions, or remain uncertain.
            # Standalone headings supply section labels but are not asserted compliant.
            substantive = [b for b in blocks if b["kind"] != "heading"] or blocks
            good = [b for b in substantive if all(any_match(group, b["text"]) for group in rule.acceptable_all)]
            if rule.id == "automatic-renewal":
                good = [b for b in good if renewal_supported(normalized(b["text"]))]
            if rule.id == "liability-cap":
                cap = next((b for b in substantive if matches(r"(?:capped|not exceed|limited to).{0,100}(?:the )?fees (?:paid|payable)", b["text"])), None)
                cap = cap if not contextual else None
                props = {"explicit_fee_cap": bool(cap), "basis": "fees paid/payable" if cap else "unresolved", "period_months": None}
                if cap:
                    period = regex.search(r"(?:preceding|prior|previous|last)\s+(\d+)\s+months|(?P<before>\d+)\s+months before", normalized(cap["text"]), regex.I)
                    props["period_months"] = int(period[1] or period["before"]) if period else None
            if contextual:
                block, reason = contextual
                outcome = "NEEDS_REVIEW"
                issues.append(make_issue(rule, block, reason + " The lexical match does not establish compliance or an affirmative adverse term.", "NEEDS_REVIEW"))
            elif bad:
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
    rule_by_id = {r.id: r for r in playbook.rules}
    for relation in analyze_relations(document, playbook.rules, matches, normalized):
        rule_id, primary = relation.pop("rule_id"), relation.pop("primary")
        check = next(c for c in checks if c["rule_id"] == rule_id)
        issue = next((i for i in issues if i["rule_id"] == rule_id and not i["absence"]), None)
        if issue is None:
            issue = make_issue(rule_by_id[rule_id], primary,
                               "Related provisions qualify this clause. Review their combined effect before deciding whether the selected playbook position is met.", "NEEDS_REVIEW")
            issues.append(issue)
        issue.setdefault("interactions", []).append(relation)
        issue["confidence"] = "NEEDS_REVIEW"
        if check["outcome"] != "ISSUE":
            check["outcome"] = "NEEDS_REVIEW"
        check["properties"]["scope_review_required"] = True
        check["properties"]["interaction_count"] = check["properties"].get("interaction_count", 0) + 1
    if not all(validate_evidence(i, document) for i in issues):
        raise ValueError("Evidence validation failed")
    return issues, checks
