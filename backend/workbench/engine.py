"""Conservative condition evaluation with validated source spans."""
import uuid
import time
from contextvars import ContextVar
DEADLINE = ContextVar("review_deadline", default=float("inf"))
import regex
from .models import Playbook
from .relations import analyze_relations
from .safety import context_reason, assignment_prohibition, renewal_supported

_TERM_NUMBER = r"(?:\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)(?:[- ](?:one|two|three|four|five|six|seven|eight|nine))?"
_AGREEMENT_SCOPE = r"\b(?:this|the)\s+(?:(?:mutual|nondisclosure)\s+)?(?:agreement|contract|nda)\b"
_TERM_CUE = r"\b(?:term|expires?|expiration|ends?|terminates?|begins?|remains? in effect|continues? in effect|is effective)\b"
_TERM_PERIOD = rf"\b{_TERM_NUMBER}\s+(?:months?|years?)\b"
_NUMBER_WORDS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
    "eleven": "11", "twelve": "12", "thirteen": "13", "fourteen": "14",
    "fifteen": "15", "sixteen": "16", "seventeen": "17", "eighteen": "18",
    "nineteen": "19", "twenty": "20", "thirty": "30", "forty": "40",
    "fifty": "50", "sixty": "60", "seventy": "70", "eighty": "80", "ninety": "90",
}


def term_duration_months(text):
    """Return a comparable month count for one explicitly stated duration."""
    match = regex.search(rf"(?P<number>{_TERM_NUMBER})\s+(?P<unit>months?|years?)\b", text, regex.I)
    if not match:
        return None
    number = normalize_term_numbers(match["number"])
    if not regex.fullmatch(r"\d+", number):
        return None
    months = int(number)
    return months * 12 if match["unit"].lower().startswith("year") else months


def term_expiration_reference(text):
    """Return a conservative comparable endpoint for one term sentence."""
    date = regex.search(
        r"\b(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(?P<day>\d{1,2}),?\s+(?P<year>\d{4})\b"
        r"|\b(?P<iso_year>\d{4})-(?P<iso_month>0[1-9]|1[0-2])-(?P<iso_day>0[1-9]|[12]\d|3[01])\b"
        r"|\b(?P<num_month>0?[1-9]|1[0-2])/(?P<num_day>0?[1-9]|[12]\d|3[01])/(?P<num_year>\d{4})\b",
        text, regex.I,
    )
    if date:
        if date["month"]:
            months = {name.lower(): number for number, name in enumerate(
                ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"), 1
            )}
            year, month, day = int(date["year"]), months[date["month"].lower()], int(date["day"])
        elif date["iso_year"]:
            year, month, day = int(date["iso_year"]), int(date["iso_month"]), int(date["iso_day"])
        else:
            year, month, day = int(date["num_year"]), int(date["num_month"]), int(date["num_day"])
        # Validate calendar dates; invalid numeric strings stay unclassified.
        try:
            from datetime import date as calendar_date
            return ("date", calendar_date(year, month, day).isoformat())
        except ValueError:
            return None
    year = regex.search(r"\b(20\d{2})\b", text)
    if year and matches(r"\b(?:expir(?:es|ation)|ends?|terminates?)\b", text):
        return ("year", int(year[1]))
    duration = term_duration_months(text)
    return ("duration", duration) if duration is not None else None


def normalize_term_numbers(text):
    """Convert written durations to digits for the playbook's own regex checks."""
    units = r"one|two|three|four|five|six|seven|eight|nine"
    tens = r"twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety"

    def compound(match):
        return str(int(_NUMBER_WORDS[match[1].lower()]) + int(_NUMBER_WORDS[match[2].lower()]))

    text = regex.sub(rf"\b({tens})[- ]({units})\b", compound, text, flags=regex.I)
    return regex.sub(
        r"\b(" + "|".join(_NUMBER_WORDS) + r")\b",
        lambda match: _NUMBER_WORDS[match[1].lower()],
        text, flags=regex.I,
    )


def term_expiration_sentences(text):
    """Return located agreement-term sentences and their confidence.

    A confidentiality survival period is not the term of the agreement. Split
    sentences before checking so separate provisions cannot donate a duration
    to each other. Conditions and negation remain review questions.
    """
    candidates = []
    sentences = regex.split(r"[.;]\s*", text)
    for index, sentence in enumerate(sentences):
        if not matches(_TERM_CUE, sentence):
            continue
        scoped = matches(_AGREEMENT_SCOPE, sentence) or matches(
            r"\bterm\s+of\s+(?:this|the)\s+(?:(?:mutual|nondisclosure)\s+)?(?:agreement|contract|nda)\b",
            sentence,
        ) or matches(r"\b(?:initial|original|contract)\s+term\b", sentence)
        renewal_only = matches(r"\brenewal\s+term\b", sentence) and not matches(
            _AGREEMENT_SCOPE, sentence
        )
        if not scoped:
            if not renewal_only:
                continue
        period = matches(_TERM_PERIOD, sentence) or matches(
            r"\bexpir(?:es|ation)\b.{0,40}\b\d{4}\b", sentence
        )
        operative = matches(
            rf"{_AGREEMENT_SCOPE}\s+(?:(?:shall|will)\s+)?(?:expire[s]?|end[s]?|terminate[s]?|remain[s]? in effect|continue[s]? in effect|be effective|is effective|be valid|is valid|continue for).{{0,100}}(?:{_TERM_PERIOD}|\b\d{{4}}\b)"
            rf"|{_AGREEMENT_SCOPE}.{{0,60}}\bbegins?\b[^.;]{{0,100}}\band\s+continues?\s+for\s+{_TERM_PERIOD}"
            rf"|{_AGREEMENT_SCOPE}\s+(?:(?:shall|will)\s+)?have a term of\s+{_TERM_PERIOD}"
            rf"|\bterm\s+of\s+(?:this|the)\s+(?:(?:mutual|nondisclosure)\s+)?(?:agreement|contract|nda)\b.{{0,50}}(?:is|shall be|will be|lasts? for).{{0,50}}(?:{_TERM_PERIOD})"
            rf"|\b(?:initial|original|renewal)\s+term\b.{{0,60}}(?:is|shall be|will be|of|for)\s+(?:for\s+)?{_TERM_PERIOD}",
            sentence,
        )
        if not period and not operative:
            continue
        # These two common qualifications preserve a definite outside term.
        # Other conditions, including discretionary extensions, remain uncertain.
        condition_text = regex.sub(
            r"\bunless\s+(?:ended|terminated)\s+earlier(?:\s+under\s+(?:(?:this|the)\s+)?(?:agreement|contract|nda))?\s*$"
            r"|\bsubject\s+to\s+early\s+termination\s*$",
            " ", sentence, flags=regex.I,
        )
        conditional_or_negated = matches(
            r"\b(?:does not|do not|did not|will not|shall not|may not|never|unless|subject to|except(?: as| for)?|provided(?: that)?|so long as|if)\b",
            condition_text,
        )
        if index + 1 < len(sentences):
            conditional_or_negated = conditional_or_negated or matches(
                r"^\s*(?:unless|subject to|except(?: as| for)?|provided(?: that)?|so long as|if)\b",
                sentences[index + 1],
            )
        candidates.append((sentence, "uncertain" if conditional_or_negated or not operative or renewal_only else "explicit"))
    return candidates


def term_expiration_status(text):
    """Return explicit/uncertain/None for agreement-duration language in a block."""
    candidates = [status for _, status in term_expiration_sentences(text)]
    if not candidates:
        return None
    return "explicit" if all(status == "explicit" for status in candidates) else "uncertain"


def relation_response(relation):
    """Give a bounded request tied to a located cap exception."""
    if relation.get("kind") != "cap-exception":
        return None
    scope = relation.get("exception_scope") or "the identified category"
    if relation.get("separate_limit_located"):
        return (f"Reconcile the {scope} carveout with the separate limit. State its amount, "
                "period, covered claims, conditions, and how it interacts with the aggregate cap.")
    return (f"State whether {scope} falls within the aggregate cap. If it is carved out, "
            "propose a separate cap with a stated amount and period, and explain how the limits interact.")

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
        term_statuses = {}
        term_sentences = {}
        if rule.id == "term-expiration":
            ordered_blocks = document["blocks"]
            for index, block in enumerate(ordered_blocks):
                located_sentences = term_expiration_sentences(block["text"])
                status = ("explicit" if located_sentences and all(s == "explicit" for _, s in located_sentences)
                          else "uncertain" if located_sentences else None)
                if status == "explicit" and index + 1 < len(ordered_blocks):
                    next_text = ordered_blocks[index + 1]["text"]
                    if matches(r"^\s*(?:unless|subject to|except(?: as| for)?|provided(?: that)?|so long as|if)\b", next_text):
                        status = "uncertain"
                if status:
                    term_statuses[block["id"]] = status
                    term_sentences[block["id"]] = located_sentences
            # Conflicting base-term durations are not resolved by precedence.
            # Compare only explicit agreement-term sentences; normalize years
            # and months to a common unit so 1 year and 12 months agree.
            endpoints = {
                endpoint
                for block in ordered_blocks
                for sentence, status in term_sentences.get(block["id"], [])
                if status == "explicit"
                for endpoint in [term_expiration_reference(sentence)]
                if endpoint is not None
            }
            if len(endpoints) > 1:
                for block in ordered_blocks:
                    if term_statuses.get(block["id"]) == "explicit" and any(
                        status == "explicit" and term_expiration_reference(sentence) is not None
                        for sentence, status in term_sentences.get(block["id"], [])
                    ):
                        term_statuses[block["id"]] = "uncertain"
            known_ids = {block["id"] for block in blocks}
            blocks.extend(block for block in document["blocks"]
                          if block["id"] in term_statuses and block["id"] not in known_ids)
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
            if rule.id == "term-expiration":
                # Number words and digits express the same configured duration
                # test. Keep the user's pattern groups intact and block a
                # survival period or an unqualified duration from satisfying them.
                good = []
                for block in substantive:
                    operative_sentences = [sentence for sentence, status in term_sentences.get(block["id"], [])
                                           if status == "explicit"]
                    accepted = bool(operative_sentences) and all(
                        all(any_match(group, normalize_term_numbers(sentence))
                            for group in rule.acceptable_all)
                        for sentence in operative_sentences
                    )
                    if term_statuses.get(block["id"]) == "explicit" and accepted:
                        good.append(block)
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
                if rule.id == "term-expiration" and term_statuses.get(unknown["id"]) == "uncertain":
                    explanation = "Agreement-duration language was located, but negation, a condition, or mixed wording prevents confirming a definite term. Review the complete provision and related sections."
                elif rule.id == "term-expiration" and not term_statuses.get(unknown["id"]):
                    explanation = "A matching phrase was located, but it does not establish the agreement's term. Check whether it describes confidentiality survival or another duration."
                else:
                    explanation = "Relevant language was found, but the configured conditions do not establish an acceptable or expressly unacceptable position. Context, scope, exceptions, and cross-references require human review."
                issues.append(make_issue(rule, unknown, explanation, "NEEDS_REVIEW"))
        checks.append(dict(rule_id=rule.id, category=rule.category, outcome=outcome, properties=props))
    rule_by_id = {r.id: r for r in playbook.rules}
    relation_responses = {}
    for relation in analyze_relations(document, playbook.rules, matches, normalized):
        rule_id, primary = relation.pop("rule_id"), relation.pop("primary")
        check = next(c for c in checks if c["rule_id"] == rule_id)
        issue = next((i for i in issues if i["rule_id"] == rule_id and not i["absence"]), None)
        if issue is None:
            issue = make_issue(rule_by_id[rule_id], primary,
                               "Related provisions qualify this clause. Review their combined effect before deciding whether the selected playbook position is met.", "NEEDS_REVIEW")
            issues.append(issue)
        issue.setdefault("interactions", []).append(relation)
        response = relation_response(relation)
        if response:
            relation_responses.setdefault(issue["id"], []).append(response)
        issue["confidence"] = "NEEDS_REVIEW"
        if check["outcome"] != "ISSUE":
            check["outcome"] = "NEEDS_REVIEW"
        check["properties"]["scope_review_required"] = True
        check["properties"]["interaction_count"] = check["properties"].get("interaction_count", 0) + 1
    for issue in issues:
        responses = list(dict.fromkeys(relation_responses.get(issue["id"], [])))
        if responses:
            issue["negotiating_response"] = " ".join(responses)
    if not all(validate_evidence(i, document) for i in issues):
        raise ValueError("Evidence validation failed")
    return issues, checks
