"""Conservative scope checks, not a general legal-language parser.

A lexical match is not an affirmative proposition when negation, an unresolved
reference, or mixed scope changes its meaning. Such cases require human review.
"""
import regex

EXTRACTION_REVISION = 2
REVIEW_REVISION = 2
LEGACY_WARNING = "Historical review: not verified by the current extraction and review checks. Re-upload the original and run a new review."


def search(pattern, text):
    return bool(regex.search(pattern, text, regex.I | regex.S, timeout=0.025))


def assignment_prohibition(text):
    """Recognize complete consent prohibitions, not a substring in a permission."""
    sentences = [s.strip() for s in regex.split(r"[.;]\s*", text) if s.strip()]
    core = r"neither party may assign this (?:agreement|contract) without (?:the )?other party(?:'s)? (?:prior )?written consent"
    repeat = r"assignment is prohibited without (?:prior )?(?:written )?consent"
    return bool(sentences and regex.fullmatch(core, sentences[0], regex.I) and
                all(regex.fullmatch(repeat, s, regex.I) for s in sentences[1:]))


def context_reason(rule_id, text, *, adverse_match=False):
    """Return a reason to abstain; never infer the opposite legal conclusion."""
    obligation_text = text
    if rule_id == "indemnification" and adverse_match and search(r"\bobligations (?:are|shall be) uncapped\b", text):
        # An affirmative uncapped obligation remains an adverse finding when a
        # second phrase confirms that the liability cap does not apply.
        obligation_text = regex.sub(r"\bnot subject to\b", "", text, flags=regex.I)
    if search(r"\b(?:not (?:required|obliged|obligated|subject to|limited to)|need not|does not require|do not require)\b", obligation_text):
        return "A negated obligation or limit changes the scope of the matched words."
    if search(r"\b(?:subject to|except (?:as|under|for)|notwithstanding|as (?:provided|defined) in)\s+(?:the\s+)?(?:section|schedule|exhibit|appendix|clause)\b", text):
        return "A cross-reference or qualification needs resolution against the complete agreement."
    if search(r"\b(?:except as otherwise|unless otherwise|subject to separate|including but not limited to|any other breach)\b", text):
        return "An open-ended qualification prevents a narrow conclusion."
    if rule_id == "liability-cap" and search(r"\bindemn", text):
        return "The same block combines a liability cap with indemnity scope; review the allocation together."
    # A prohibition of unfavorable conduct is not permission for that conduct.
    if adverse_match and search(r"\b(?:neither party|no party|shall not|must not|is prohibited|may not)\b", text):
        if rule_id == "assignment" and assignment_prohibition(text):
            return None
        if rule_id == "automatic-renewal" and search(r"customer may not (?:cancel|opt out)", text):
            return None  # directly prohibits the customer's opt-out, a configured adverse condition
        return "The matched adverse words occur with a prohibition; permission and scope are unresolved."
    if rule_id == "automatic-renewal" and search(r"\b(?:may not|shall not|must not|neither party)\b", text):
        return "Negation prevents confirming a renewal opt-out."
    return None


def renewal_supported(text):
    """Tie notice to nonrenewal, not an unrelated deadline in the same block."""
    if search(r"(?:does not renew automatically|(?:no|without) automatic renewal)", text):
        # Do not let one acceptable sentence mask a contradictory second sentence.
        rest = regex.sub(r"(?:does not renew automatically|(?:no|without) automatic renewal)", "", text, flags=regex.I)
        return not search(r"renew(?:s|ed)? automatically|automatic(?:ally)? renew", rest)
    return search(r"(?:either|each) party (?:may (?:give|deliver|provide)|gives?|delivers?|provides?) (?:written )?notice of non.?renewal (?:at least )?(?:30|60) days before (?:the )?(?:term|agreement) (?:ends|expires)", text)


def review_view(review):
    """Derive status at read/export time; preserve historical stored decisions."""
    current = review.get("review_revision") == REVIEW_REVISION
    rules = {r["id"]: r for r in review.get("playbook_snapshot", {}).get("rules", [])}
    issues = []
    for issue in review["issues"]:
        rule = rules.get(issue["rule_id"], {})
        issues.append({**issue, "playbook_guidance": {
            "acceptable_alternatives": rule.get("acceptable_alternatives", []),
            "fallback_language": rule.get("fallback_language"),
        }})
    return {**review, "issues": issues, "verification_status": "CURRENT_CHECKS" if current else "HISTORICAL_UNVERIFIED",
            "verification_warning": None if current else LEGACY_WARNING}
