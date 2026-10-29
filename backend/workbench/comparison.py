"""Read-only review comparisons. Text equality never proves legal equivalence."""
from collections import defaultdict
from difflib import SequenceMatcher
import hashlib
import json


def text_digest(document):
    return hashlib.sha256(document["text"].encode()).hexdigest()


def _finding_signature(issue):
    # Keep evidence and scope; omit random IDs, offsets, notes and decisions.
    def anchor(value):
        return value.get("text") if value else None
    result = {key: issue.get(key) for key in (
        "severity", "absence", "confidence", "origin", "observed_language",
        "explanation", "preferred_position", "negotiating_response")}
    result["source"] = anchor(issue.get("source_anchor"))
    result["interactions"] = [
        {**{k: v for k, v in relation.items() if k != "evidence"},
         "evidence": [anchor(a) for a in relation.get("evidence", [])]}
        for relation in issue.get("interactions", [])
    ]
    return json.dumps(result, sort_keys=True)


def compare_reviews(before, after, old_document, new_document):
    def context(review):
        return {key: review.get(key) for key in (
            "id", "created_at", "playbook_id", "playbook_name", "playbook_snapshot",
            "review_revision", "extraction_revision", "verification_status", "ai_status")}
    old_blocks, new_blocks = old_document["blocks"], new_document["blocks"]
    # Paragraph comparison is bounded by the parser's 5,000-block limit.
    matcher = SequenceMatcher(None, [b["text"] for b in old_blocks],
                              [b["text"] for b in new_blocks], autojunk=True)
    changes = [{"kind": kind, "before": old_blocks[i:j], "after": new_blocks[k:l]}
               for kind, i, j, k, l in matcher.get_opcodes() if kind != "equal"]
    policy_same = before.get("playbook_snapshot") == after.get("playbook_snapshot")
    checks_same = all(before.get(k) is not None and before.get(k) == after.get(k)
                      for k in ("extraction_revision", "review_revision"))
    text_same = old_document["text"] == new_document["text"]
    original_same = old_document["sha256"] == new_document["sha256"]
    context_changed = not (policy_same and checks_same and text_same and original_same)
    grouped = []
    issue_groups = []
    for review in (before, after):
        groups = defaultdict(list)
        for issue in review["issues"]:
            groups[issue["rule_id"]].append(issue)
        issue_groups.append(groups)
    check_maps = [{c["rule_id"]: c for c in review["checks"]} for review in (before, after)]
    for rule in sorted(set(check_maps[0]) | set(check_maps[1]) | set(issue_groups[0]) | set(issue_groups[1])):
        old, new = issue_groups[0][rule], issue_groups[1][rule]
        old_check, new_check = check_maps[0].get(rule), check_maps[1].get(rule)
        if not policy_same or not checks_same:
            status = "NOT_COMPARABLE"
        elif not old and new:
            status = "ADDED"
        elif old and not new:
            status = "NO_LONGER_FLAGGED"
        elif (sorted(map(_finding_signature, old)) != sorted(map(_finding_signature, new))
              or old_check != new_check):
            status = "CHANGED"
        else:
            status = "UNCHANGED"
        prior_decisions = [{"issue_id": i["id"], "status": i["status"], "notes": i["notes"],
                            "source_anchor": i.get("source_anchor")}
                           for i in old if i["status"] != "unresolved" or i["notes"]]
        grouped.append({"rule_id": rule, "category": (new_check or old_check or (new or old)[0])["category"],
                        "status": status, "before_check": old_check, "after_check": new_check,
                        "before_issues": old, "after_issues": new,
                        "prior_decisions": prior_decisions,
                        "revisit_prior_decisions": bool(prior_decisions and context_changed)})
    warnings = ["A finding that is no longer flagged is not a legal clearance. Text comparison does not assess legal equivalence.",
                "Decisions and notes remain in their original review. No decisions are copied."]
    if context_changed:
        warnings.append("Revisit earlier decisions: changed language, source bytes, policy or checks can affect other clauses, including apparently unchanged findings.")
    if not policy_same:
        warnings.append("Saved policies differ. Finding differences cannot be attributed solely to contract edits.")
    if not checks_same:
        warnings.append("Extraction or analysis versions differ. Finding differences cannot be attributed solely to contract edits.")
    if any(not review.get("source_text_sha256") for review in (before, after)):
        warnings.append("An earlier review has no saved text digest. Its quoted evidence was checked against the retained extraction, but full historical text identity cannot be independently verified.")
    if text_same and not original_same:
        warnings.append("Extracted text is identical but original files differ. Formatting, images or omitted content may have changed; compare both originals.")
    warnings.extend(dict.fromkeys([*(old_document.get("warnings") or []), *(new_document.get("warnings") or [])]))
    warnings.extend(dict.fromkeys(review["verification_warning"] for review in (before, after) if review.get("verification_warning")))
    return {"comparison_version": 1, "author": "Ethan", "before_review_id": before["id"],
            "after_review_id": after["id"],
            "before_context": context(before), "after_context": context(after),
            "before_document": {k: old_document[k] for k in ("id", "name", "sha256")},
            "after_document": {k: new_document[k] for k in ("id", "name", "sha256")},
            "same_policy": policy_same, "same_checks": checks_same,
            "same_extracted_text": text_same, "same_original": original_same,
            "warnings": warnings, "text_changes": changes, "rules": grouped}
