# Playbook schema version 1

Author: Ethan

Playbooks are UTF-8 YAML documents, validated with Pydantic. Unknown fields, duplicate mapping keys, duplicate rule IDs, aliases, anchors, invalid regexes, and excessive input are rejected. The UI can create, duplicate, edit, import, and export playbooks. Start by duplicating the bundled playbook; change its name/version and relevant rules. An old review keeps its own snapshot.

Top-level fields: `schema_version: 1`, `name`, `version`, `description`, and `rules` (1–100 entries).

Each rule has:

| Field | Meaning |
| --- | --- |
| `id` | Stable unique lowercase rule ID, letters/digits/hyphens |
| `category` | Clause category shown in findings |
| `description` | Review purpose |
| `preferred_position` | Preferred language or position |
| `acceptable_alternatives` | Human-readable acceptable alternative guidance |
| `unacceptable_conditions` | Human-readable unacceptable condition guidance |
| `severity` | `high`, `medium`, or `low` |
| `required` | Missing candidate language produces an absence finding if true |
| `negotiation_guidance` | Suggested negotiating response |
| `fallback_language` | Optional fallback text or null |
| `presence` | Any pattern locates a relevant source block |
| `acceptable_all` | All groups must match; any pattern within each group suffices |
| `unacceptable_any` | Any match in relevant blocks reports an issue |

Patterns use the Python `regex` package with case-insensitive and dot-all matching, bounded execution time, and a 500-character pattern limit. Matching normalizes newlines, typographic apostrophes and common number words (twelve/thirty/sixty/ninety). Source text remains exact. Patterns are not arbitrary Python code. Human-readable alternatives are guidance, not hidden inference: encode an objectively testable alternative in `acceptable_all`, or expect a human to assess it.

Example:

```yaml
schema_version: 1
name: Limited liability screen
version: 1.0.0
description: Illustrative fee-based cap policy requiring attorney review.
rules:
  - id: fee-cap
    category: Limitation of liability
    description: Screen for an explicit fee-based cap.
    preferred_position: Aggregate liability capped at fees paid in the preceding 12 months.
    acceptable_alternatives: [A separately negotiated monetary cap approved by counsel.]
    unacceptable_conditions: [Expressly unlimited aggregate liability.]
    severity: high
    required: true
    negotiation_guidance: Request a defined aggregate cap and separately review exceptions.
    fallback_language: null
    presence: ['aggregate liability']
    acceptable_all:
      - ['not exceed.{0,50}fees paid']
      - ['preceding 12 months']
    unacceptable_any: ['unlimited|uncapped']
```

The commercial playbook contains all 18 specified categories. The NDA playbook contains confidentiality, exclusions, permitted disclosures, term, governing law, and assignment. Neither template is jurisdiction-neutral legal advice. Rules with an absent requirement express a search failure and require review of the full original. COMPLIANT means only that the configured conditions matched; it is not a legal certification.
