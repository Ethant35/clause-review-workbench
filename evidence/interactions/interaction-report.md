# Contract review report

Document: cap-exception-supercap.docx
Playbook: Interaction acceptance liability-cap
AI status: NOT_REQUESTED
Contract review aid, not legal advice. Attorney review is required.

Source SHA256: fa425dc7467b8a035dce8da4994e3d4c3af6f6a44a907d6645ec491153abfa45

## Limitation of liability

**Issue ID:** 96b343e1-00dc-4cc5-a5e0-28b02e4a8a4f

**Rule ID:** liability-cap

**Severity:** high

**Clause category:** Limitation of liability

**Observed language:** Each party’s aggregate liability will not exceed the Fees paid in the preceding twelve months.

**Source anchor:** b1; Paragraph 1; extracted offsets [0, 94)

**Explanation:** Related provisions qualify this clause. Review their combined effect before deciding whether the selected playbook position is met.

**Related clauses and effect:** cap-exception: A separate provision removes a named category from the base liability cap. The base fee formula does not describe all covered exposure. A separate limit for the same named category was also located. Check scope, conditions and precedence together; do not label the whole agreement uncapped.
b1; Paragraph 1; extracted offsets [0, 94): Each party’s aggregate liability will not exceed the Fees paid in the preceding twelve months.
b2; Paragraph 2; extracted offsets [96, 160): The liability cap does not apply to indemnification obligations.
b3; Paragraph 3; extracted offsets [162, 257): Indemnification liability is limited to two times the Fees paid in the preceding twelve months.

**Preferred contract position:** Express aggregate cap based on fees paid or payable in the preceding 12 months.

**Suggested negotiating response:** Request a revision that provides: Express aggregate cap based on fees paid or payable in the preceding 12 months.

**Saved playbook alternatives and fallback:** Playbook guidance only; not contract text or a verified legal standard. Alternatives: A specifically negotiated, documented allocation approved by counsel.
Fallback wording: None specified

**Reviewer status:** unresolved

**Reviewer notes:** (none)

**Confidence or uncertainty:** NEEDS_REVIEW

**Analysis layer:** deterministic

## Rule checks

- liability-cap: NEEDS_REVIEW {&quot;explicit_fee_cap&quot;: true, &quot;basis&quot;: &quot;fees paid/payable&quot;, &quot;period_months&quot;: 12, &quot;scope_review_required&quot;: true, &quot;interaction_count&quot;: 1}