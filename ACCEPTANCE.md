# Local acceptance for v1.1.0

Author: Ethan. Date: October 22, 2026 (America/Los_Angeles).

**Core offline workbench: PASS. AI-assisted review: UNVERIFIED / BLOCKED_EXTERNAL.** The specification explicitly permits a core release when valid AI credentials are unavailable. Do not describe this release's AI interpretation as production-verified.

GitHub Actions are intentionally omitted and disabled at repository level per Ethan. No workflows were created or dispatched. CI is not claimed to pass. Equivalent installation, real database, browser, ingestion, corpus, exports, and privacy gates ran locally.

## Environment and reproducibility

macOS arm64; Python 3.12.14; Node v22.13.1; locked Python and npm dependencies; Playwright Chromium. The clean checkout tested application commit `f1f77f5`. Later release-document/evidence commits do not change application behavior. Run:

```sh
./scripts/clean_acceptance.sh
./scripts/package.sh
.venv/bin/python scripts/deployment_smoke.py artifacts/clause-review-workbench-1.0.1.tar.gz
```

The clean-install script clones locally to a new directory, installs a new Python environment, runs npm ci and the production build, starts the real application with fresh SQLite storage, and exercises Chromium. The archive smoke test extracts to another new directory, runs the packaged startup command, and completes a browser review/export. No unit tests, mocked parsers, fake databases, or fake LLM responses were used.

Evidence: [E2E results](evidence/interactions/e2e-results.json), [corpus scoring](evidence/interactions/corpus-results.json), [archive deployment](evidence/interactions/package-result.json), [npm audit](evidence/interactions/npm-audit.json), and [workbench screenshot](evidence/interactions/workbench.png).

## Required matrix

| Test | Status | Observed result |
| --- | --- | --- |
| CR-01 Clean installation | PASS | Fresh clone, locked installation, frontend build, server and Chromium workflows |
| CR-02 DOCX ingestion | PASS | Real DOCX; exact body paragraph equality, original bytes unchanged, anchored findings |
| CR-03 PDF ingestion | PASS | Real two-page text PDF; exact blocks and page anchors; both planted findings |
| CR-04 Plain text | PASS | Browser upload and review; extracted lines exactly match source |
| CR-05 Invalid input | PASS | Binary/unsupported/corrupt/empty/oversized files and image-only PDF rejected; safe filename handling |
| CR-06 NDA evaluation | PASS | Browser review reports six compliant checks and no findings |
| CR-07 Renewal and audit | PASS | Both planted deviations found with validated source passages |
| CR-08 Liability | PASS | Explicit fees-paid cap and 12-month basis identified; narrow exceptions assessed separately |
| CR-09 Missing provision | PASS | Missing DPA flagged with null quote and anchor; no invented text |
| CR-10 IP assignment | PASS | Broad pre-existing IP transfer found and cited |
| CR-11 Playbook editing | PASS | UI duplicate/edit changes severity on rerun; prior review unchanged; YAML import/export; saved fallback guidance survives later playbook edits |
| CR-12 Reviewer workflow | PASS | Accept/reject/unresolved and notes persist across server restart |
| CR-13 Source navigation | PASS | Browser selection displays exact quoted block; original location retained |
| CR-14 Exports | PASS | Markdown, DOCX, JSON opened and required fields plus saved policy guidance verified; browser downloads succeed |
| CR-15 Deletion | PASS | Browser deletion removes original, metadata, and all associated reviews |
| CR-16 Full corpus | PASS | All 12 independent manifests match objective/uncertain outcomes |
| CR-17 Local privacy | PASS | Zero backend outbound socket connections and zero external browser requests through offline workflows; consent/missing-key gates verified |
| CR-18 Real AI | BLOCKED_EXTERNAL | OPENROUTER_API_KEY, OPENROUTER_MODEL, and OPENROUTER_PROVIDER absent; no simulated result |
| CR-19 AI errors | PASS | Real OpenRouter authentication request with deliberately invalid credential rejected; original and offline review preserved |
| CR-20 Fresh deployment | PASS | Fresh SQLite database; unseen synthetic contract uploaded, reviewed, accepted, exported in browser |

Additional E2E checks passed for conflicting liability provisions, safe literal display of script-like content, retention-triggered cascading deletion, hostile Host/Origin rejection, and YAML alias rejection. The deployment archive independently passed startup, upload, findings, reviewer decision, and export from fresh extraction. npm audit reported zero vulnerabilities at the recorded check.

## Corpus scoring

The twelve synthetic contracts and expectations were authored independently before application analysis ran. Stable rule IDs drive scoring. There are 11 planted objective deviations, 191 compliant controls, and two expected uncertain cap outcomes: one ambiguous formula and one cap qualified by an indemnity exception.

- Scenarios passed: 12/12.
- Planted deviations detected: 11/11.
- False positives: 0.
- False negatives: 0.
- Failed compliant controls: 0/191.
- Citation mismatches: 0.
- Ambiguous expected outcomes: 2/2 reported NEEDS_REVIEW.

Absence-based deviations are expected objective search outcomes but retain NEEDS_REVIEW confidence: absence of a pattern is not proof that a legal obligation is absent. Quotation-bearing findings exactly resolve to extracted source text. Results are not a measure of universal legal accuracy, recall, or enforceability.

## Visual and metadata checks

The changed interaction view, exact source navigation, and 390-pixel mobile workbench were inspected; no horizontal overflow occurred at 390 pixels. Compact tool headings replaced welcome/marketing copy. The generated one-page interaction report was rendered through LibreOffice and visually inspected. Earlier fixture layout evidence remains in evidence/quality. Required report data survived opening with python-docx and JSON/Markdown readers. DOCX author and last-modified-by fields, and PDF fixture author, were verified as Ethan. Original uploads are preserved byte-for-byte; their metadata is never rewritten. Finder/Windows shell metadata displays were not separately verified.

## New interaction and upgrade acceptance

- 31 authored cases across TXT/DOCX/PDF, plus resource limits, inactive-rule isolation, browser persistence/navigation/mobile layout and offline audit: 98/98 checks passed.
- All related blocks match exact extracted offsets and authored text; Markdown, DOCX and JSON retain the explanations and evidence.
- The same initial 26-case suite plus network audit improved from 31/79 before implementation to 79/79. Extra cases were added as edge defects were reproduced; the 98-check total is not presented as the original baseline denominator.
- Existing adversarial suite: 81/81 unchanged expectations.
- Real released-server upgrades: six checks each from v1.0.0 and v1.0.1. Stored rows/notes/source remain intact; current extraction can be rerun without re-upload, while older extraction cannot.
- Original scenario 06 now expects NEEDS_REVIEW for the base cap, in addition to its two objective deviations. The removed compliant-control expectation had ignored the uncapped-indemnity exception. This is an intentional correction, not unchanged-suite equivalence.

Evidence: interactions-before.json, interactions-results.json, adversarial-results.json, upgrade-results.json and upgrade-v1.0.1-results.json under evidence/interactions. These synthetic expectations are agent-authored; they are not independent lawyer validation.

## Limitations

Pattern conditions cover narrow drafting forms. Negations, definitions, cross-references, unusual layouts, exceptions, and broader legal context may need manual review and can fall outside a rule's recognition. COMPLIANT means configured conditions matched, not that the agreement is legally sufficient. Governing-law guidance is configurable and illustrative.

OCR and encrypted PDFs are unsupported. PDFs with raster images (including logos) or textless pages are rejected. DOCX revisions/macros/text boxes/notes/imports/content controls/fields/drawings and directly marked hidden text are unsupported. DOCX headers/footers are excluded with a visible warning. Verify full originals. This is a single-user loopback application without authentication or application-level encryption; not a public-hosting service. Deletion does not erase exports, backups, or guarantee SSD forensic erasure. The OpenRouter adapter, consent, budgets, and citation gates are implemented, but successful live AI interpretation remains unverified until CR-18 can run with authorized credentials.

## Corrective evidence: v1.0.0 to v1.0.1

The prior twelve-contract corpus did not expose important failures. The expanded suite fixes its expectations before running the application, uses authored text rather than the application's parser as the extraction oracle, and includes paired positive/negated examples in TXT, DOCX, and PDF. Its expectations are agent-authored, not a lawyer-panel or held-out benchmark.

| Check | Before | After |
| --- | --- | --- |
| 24 semantic cases across three real file formats | Included in 31/81 overall passes | 72/72 pass |
| Eight OOXML/PDF structural cases | Incomplete/hidden content sometimes accepted | 8/8 pass |
| Offline outbound socket audit | Pass | Pass |
| Total fixed adversarial checks | 31/81 pass; 50 fail | 81/81 pass |
| Original corpus | 12/12 pass | 12/12 pass |
| Real released-server upgrade | Not previously tested | 6/6 pass |

Evidence: [before](evidence/quality/adversarial-before.json), [after](evidence/quality/adversarial-after.json), [upgrade](evidence/quality/upgrade-results.json). The unchanged 81-check suite is a bounded regression set. It does not measure general legal correctness or exhaustive extraction safety.

The upgrade suite creates its initial records through an actual v1.0.0 server, then runs the new server against the same database. It verifies original bytes, raw stored rows, accepted decisions, notes, historical warnings in API/browser/all exports, refusal to reuse old extraction, browser re-upload and new uncertainty outcome, and no backend outbound connection. Existing reviews stay historical; their legal results are not silently re-certified.

The new policy panel and export fields use each review's saved playbook snapshot. E2E changes a policy after review, reloads the browser, and checks that the old fallback persists in the UI and all report formats. Unspecified fallback remains unspecified. All personal DOCX author/last-modified-by fields remain Ethan. A rendered two-page current report and the browser warning were inspected. Finder/Windows shell displays were not separately verified.

See [RESEARCH.md](RESEARCH.md) for current Astra for Law access evidence, professional/user anecdotes, public GitHub sources, parser documentation, and explicit limits. No private legal index, Astra for Law access, new provider, or fake model result is included. GitHub Actions remain disabled and all verification is local. Root-level evidence files are retained as the historical v1.0.0 record; the quality subdirectory contains this patch's results.
