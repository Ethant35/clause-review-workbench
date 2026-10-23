"""Bounded cross-clause evidence, not a general legal-effect or precedence solver.

Recognizers report named dependencies. They never declare enforceability, select
party preferences, calculate damages, or silently treat located text as resolved law.
"""
import regex

# Only explicit section/clause labels are indexed. Bare numbered paragraphs,
# external documents and plural/range references are not guessed.
NUMBER = r"\d+(?:\.\d+)*(?:\([a-z0-9]+\))*"
LABEL = regex.compile(r"^\s*(?:section|clause)\s+(" + NUMBER + r")(?:[.:]|\s+-)?\s+", regex.I)
QUALIFIER = regex.compile(
    r"\b(?:subject to|except (?:as provided in|as set out in|under|for)|notwithstanding|as (?:provided|defined) in)\s+"
    r"(?:the\s+)?(?P<type>sections?|clauses?|schedule|exhibit|appendix)\s+"
    r"(?P<label>" + NUMBER + r"|[a-z]+)(?![\w(])", regex.I)

# Explicit drafting variants that tie a named obligation to an earlier cap.
# Keep these forms narrow: generic uses of "excluded" or "limitations" may
# concern remedies other than the liability cap.
CAP_EXCLUSION = regex.compile(
    r"\b(?:indemn\w*|confidential\w*|data protection|security|intellectual property|payment)\b"
    r".{0,100}\b(?:is|are|shall be)\s+(?:expressly\s+)?excluded from\s+"
    r"(?:the\s+)?(?:foregoing|above|aforesaid)\s+(?:liability\s+)?(?:cap|limitations?|limits?)\b"
    r"|\b(?:indemn\w*|confidential\w*|data protection|security|intellectual property|payment)\b"
    r".{0,100}\b(?:is|are|shall be)\s+not subject to\s+(?:the\s+)?(?:liability\s+)?(?:cap|limitations?|limits?)\b"
    r"|\b(?:the\s+)?(?:foregoing|above|aforesaid)\s+(?:liability\s+)?(?:cap|limitations?|limits?)\s+"
    r"(?:do not|does not|shall not)\s+apply to\s+.{0,100}\b(?:indemn\w*|confidential\w*|data protection|security|intellectual property|payment)\b",
    regex.I,
)


class InteractionLimit(ValueError):
    pass


def analyze_relations(document, rules, matches, normalized):
    blocks = document['blocks']
    text = {b['id']: normalized(b['text']) for b in blocks}
    active = {r.id: r for r in rules}
    results = []
    seen = set()

    def unique(items):
        return list({b['id']: b for b in items}.values())

    def add(rule_id, primary, kind, explanation, evidence, **extra):
        evidence = unique([primary, *evidence])
        key = (rule_id, primary['id'], kind, tuple(b['id'] for b in evidence), extra.get('reference'))
        if key in seen:
            return
        # Fail explicitly rather than truncate and assert a complete review.
        if len(results) >= 100 or len(evidence) > 64:
            raise InteractionLimit('Too many linked clauses for bounded analysis. Review a smaller document or the complete agreement manually.')
        seen.add(key)
        results.append(dict(rule_id=rule_id, primary=primary, kind=kind, explanation=explanation, evidence=evidence, **extra))

    caps = [b for b in blocks if matches(r'\b(?:aggregate|total|overall) liability.{0,160}(?:not exceed|capped|limited to).{0,100}\bfees\b', text[b['id']])]
    if 'liability-cap' in active and caps:
        definitions = [b for b in blocks if matches(r'(?:["“]Fees["”]|\bFees)\s+(?:means|shall mean|is defined as)\b', text[b['id']])]
        restricted = [b for b in definitions if matches(r'\b(?:only|exclud\w*|but not|does not include|limited to)\b', text[b['id']])]
        if len(definitions) > 1 or restricted:
            explanation = ('Multiple definitions of Fees were located. Confirm which definition controls the cap; do not select one silently.'
                           if len(definitions) > 1 else
                           'The cap uses Fees, while its definition narrows or excludes amounts. A twelve-month period alone does not establish the monetary protection. Confirm the included charges and applicable definition.')
            for cap in caps:
                add('liability-cap', cap, 'fee-definition', explanation, definitions)

        for exception in blocks:
            source = text[exception['id']]
            carveout = regex.search(r'\b(?:the\s+)?liability cap (?:does not|shall not) apply to\s+([^.;]+)', source, regex.I, timeout=.025)
            uncapped = matches(r'\bindemnification (?:liability|obligations) (?:is|are|shall be) (?:uncapped|unlimited)\b', source)
            named_exclusion = CAP_EXCLUSION.search(source, timeout=.025)
            if not carveout and not uncapped and not named_exclusion:
                continue
            category_terms = (
                (r'indemn\w*', 'indemnification'),
                (r'confidential\w*', 'confidentiality'),
                (r'data protection', 'data protection'),
                (r'security', 'security'),
                (r'intellectual property', 'intellectual property'),
                (r'payment', 'payment'),
            )
            categories = [(pattern, label) for pattern, label in category_terms if matches(pattern, source)]
            scope = carveout[1].strip() if carveout else ', '.join(label for _, label in categories) if named_exclusion else 'indemnification'
            # These two categories are the bundled playbook's stated narrow
            # exceptions. Other allocations remain review questions, not errors.
            if carveout and regex.fullmatch(r'(?:fraud|willful misconduct)(?:\s*(?:,|and|or)\s*(?:fraud|willful misconduct))*', scope, regex.I) and not uncapped:
                continue
            separate = [b for b in blocks if b not in caps and b != exception and
                        any(matches(pattern, text[b['id']]) for pattern, _ in categories) and
                        matches(r'\bliability (?:is|shall be) (?:limited to|capped at|not to exceed)\b', text[b['id']])]
            explanation = f'A separate provision removes {scope} from the base liability cap. The base fee formula does not describe all covered exposure. '
            if separate:
                explanation += f'A separate limit for {scope} was also located. Check scope, conditions and precedence together; do not label the whole agreement uncapped.'
                if uncapped or matches(r'\b(?:uncapped|unlimited)\b', source):
                    explanation += 'Express uncapped wording and a separate limit may conflict; no priority is inferred.'
            else:
                explanation += 'An exception to the base cap alone does not establish unlimited exposure; verify any category-specific limit and other remedies.'
            for cap in caps:
                add('liability-cap', cap, 'cap-exception', explanation, [exception, *separate])
                if 'indemnification' in active and any(pattern == r'indemn\w*' for pattern, _ in categories):
                    add('indemnification', exception, 'cap-exception', explanation, [cap, *separate])

    if 'termination-convenience' in active:
        rights = [b for b in blocks if matches(r'\b(?:either|each) party may terminate.{0,60}\bfor convenience\b', text[b['id']])]
        for cost in blocks:
            source = text[cost['id']]
            payable_on_exit = False
            for sentence in regex.split(r'[.;]', source, timeout=.025):
                condition = matches(r'\b(?:upon|on|following|in the event of) termination for convenience\b|\bif\b[^.;]{0,60}\bterminates? for convenience\b', sentence)
                excluded = matches(r'\b(?:except|other than|excluding)\s+(?:(?:upon|on|following) )?termination for convenience\b', sentence)
                payment = matches(r'\b(?:shall|must|will) pay (?:all |the )?remaining fees\b|\bprepaid fees (?:will|shall) not be refunded\b|\bno refund of (?:unused )?prepaid fees\b', sentence)
                payable_on_exit = payable_on_exit or (condition and payment and not excluded)
            if payable_on_exit:
                for right in rights:
                    add('termination-convenience', right, 'termination-cost',
                        'The convenience termination right is paired with remaining-term payment or retained prepaid fees. The right to exit does not itself eliminate those costs. Confirm the trigger, amounts and any overriding refund provision.', [cost])

    # An exact target is evidence, not a conclusion about its legal effect.
    sections = {}
    current = None
    for block in blocks:
        match = LABEL.match(text[block['id']], timeout=.025)
        if match:
            current = []
            sections.setdefault(match[1].lower(), []).append(current)
        if current is not None:
            current.append(block)

    def references(block):
        for match in QUALIFIER.finditer(text[block['id']], timeout=.025):
            if regex.search(r'\bnot\s*$', text[block['id']][:match.start()], regex.I, timeout=.025):
                continue  # a negated dependency is already handled by the scope guard
            kind, label = match['type'].lower(), match['label'].lower()
            tail = text[block['id']][match.end():]
            if kind in ('schedule', 'exhibit', 'appendix'):
                status = 'external'
            elif kind.endswith('s') or regex.match(r'\s*(?:and|or|through|to|[-–])\s*\d', tail, regex.I, timeout=.025):
                status = 'unsupported'
            elif not regex.fullmatch(NUMBER, label, regex.I):
                status = 'unsupported'
            else:
                status = None
            yield kind, label, status

    def trace(kind, label, status, path=(), budget=None):
        if budget is None:
            budget = [64]
        budget[0] -= 1
        if budget[0] < 0:
            return 'limit', []
        if status:
            return status, []
        if label in path:
            return 'cycle', []
        if len(path) >= 6:
            return 'limit', []
        targets = sections.get(label, [])
        if not targets:
            return 'missing', []
        evidence = unique([b for target in targets for b in target])
        if len(evidence) > 64:
            raise InteractionLimit('A referenced section exceeds the 64-block evidence limit. Review the complete agreement manually.')
        if len(targets) != 1:
            return 'ambiguous', evidence
        statuses = []
        for block in targets[0]:
            matches(r'\A', text[block['id']])  # honor the shared analysis deadline
            for child in references(block):
                result, related = trace(*child, (*path, label), budget)
                statuses.append(result)
                evidence = unique([*evidence, *related])
                if len(evidence) > 64:
                    raise InteractionLimit('A reference chain exceeds the 64-block evidence limit. Review the complete agreement manually.')
        return next((s for s in statuses if s != 'located'), 'located'), evidence

    descriptions = {
        'located': 'The qualified reference and its supported reference chain were located. Read the linked text together; location does not resolve legal effect, priority or compliance.',
        'missing': 'A qualified reference points to a section that was not located by its explicit label. Obtain the missing text or verify numbering before relying on the provision.',
        'ambiguous': 'More than one section has the referenced label. No controlling version was selected; resolve the duplicate labels and precedence.',
        'cycle': 'The qualified reference chain is circular. The linked provisions require manual reconciliation; no controlling term was inferred.',
        'limit': 'The reference chain exceeds the six-section or 64-visit traversal limit. The displayed evidence is incomplete; review the remaining chain manually.',
        'external': 'The provision depends on a schedule, exhibit or appendix. This analyzer does not establish that incorporated document’s completeness or effect; verify the controlling version.',
        'unsupported': 'The qualifier uses a reference form this analyzer cannot resolve safely, such as a range or multiple sections. Resolve each target manually.',
    }
    for rule in rules:
        for block in blocks:
            if not any(matches(p, text[block['id']]) for p in rule.presence) and not (rule.id == 'liability-cap' and block in caps):
                continue
            for kind, label, status in references(block):
                status, evidence = trace(kind, label, status)
                add(rule.id, block, 'qualified-reference', descriptions[status], evidence,
                    reference=f'{kind.title()} {label}', status=status)
    return results
