# Local acceptance for v1.0.0

Author: Ethan. Date: October 22, 2026 (America/Los_Angeles).

**Core offline workbench: PASS. AI-assisted review: UNVERIFIED / BLOCKED_EXTERNAL.** The specification explicitly permits a core release when valid AI credentials are unavailable. Do not describe this release's AI interpretation as production-verified.

GitHub Actions are intentionally omitted and disabled at repository level per Ethan. No workflows were created or dispatched. CI is not claimed to pass. Equivalent installation, real database, browser, ingestion, corpus, exports, and privacy gates ran locally.

## Environment and reproducibility

macOS arm64; Python 3.12.14; Node v22.13.1; locked Python and npm dependencies; Playwright Chromium. The clean checkout tested application commit `2c11357d4e2d9d4dffe9a2ce3a814301dfcb5523`. Later release-document/evidence commits do not change application behavior. Run:

```sh
./scripts/clean_acceptance.sh
./scripts/package.sh
.venv/bin/python scripts/deployment_smoke.py artifacts/clause-review-workbench-1.0.0.tar.gz
```

The clean-install script clones locally to a new directory, installs a new Python environment, runs npm ci and the production build, starts the real application with fresh SQLite storage, and exercises Chromium. The archive smoke test extracts to another new directory, runs the packaged startup command, and completes a browser review/export. No unit tests, mocked parsers, fake databases, or fake LLM responses were used.

Evidence: [E2E results](evidence/e2e-results.json), [corpus scoring](evidence/corpus-results.json), [archive deployment](evidence/package-result.json), [npm audit](evidence/npm-audit.json), and [workbench screenshot](evidence/workbench.png).

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
| CR-11 Playbook editing | PASS | UI duplicate/edit changes severity on rerun; prior review unchanged; YAML import/export |
| CR-12 Reviewer workflow | PASS | Accept/reject/unresolved and notes persist across server restart |
| CR-13 Source navigation | PASS | Browser selection displays exact quoted block; original location retained |
| CR-14 Exports | PASS | Markdown, DOCX, JSON opened and required fields verified; browser downloads succeed |
| CR-15 Deletion | PASS | Browser deletion removes original, metadata, and all associated reviews |
| CR-16 Full corpus | PASS | All 12 independent manifests match objective/uncertain outcomes |
| CR-17 Local privacy | PASS | Zero backend outbound socket connections and zero external browser requests through offline workflows; consent/missing-key gates verified |
| CR-18 Real AI | BLOCKED_EXTERNAL | OPENROUTER_API_KEY, OPENROUTER_MODEL, and OPENROUTER_PROVIDER absent; no simulated result |
| CR-19 AI errors | PASS | Real OpenRouter authentication request with deliberately invalid credential rejected; original and offline review preserved |
| CR-20 Fresh deployment | PASS | Fresh SQLite database; unseen synthetic contract uploaded, reviewed, accepted, exported in browser |

Additional E2E checks passed for conflicting liability provisions, safe literal display of script-like content, retention-triggered cascading deletion, hostile Host/Origin rejection, and YAML alias rejection. The deployment archive independently passed startup, upload, findings, reviewer decision, and export from fresh extraction. npm audit reported zero vulnerabilities at the recorded check.

## Corpus scoring

The twelve synthetic contracts and expectations were authored independently before application analysis ran. Stable rule IDs drive scoring. There are 11 planted objective deviations, 192 compliant controls, and one explicitly ambiguous liability example.

- Scenarios passed: 12/12.
- Planted deviations detected: 11/11.
- False positives: 0.
- False negatives: 0.
- Failed compliant controls: 0/192.
- Citation mismatches: 0.
- Ambiguous expected outcomes: 1/1 reported NEEDS_REVIEW.

Absence-based deviations are expected objective search outcomes but retain NEEDS_REVIEW confidence: absence of a pattern is not proof that a legal obligation is absent. Quotation-bearing findings exactly resolve to extracted source text. Results are not a measure of universal legal accuracy, recall, or enforceability.

## Visual and metadata checks

The desktop and mobile workbench were inspected; no horizontal overflow occurred at 390 pixels. Compact tool headings replaced welcome/marketing copy. A real generated DOCX report and DOCX fixture were rendered through LibreOffice and every rendered page inspected. Both PDF fixture pages were rendered and inspected. Report title/heading styling and spacing were corrected before final inspection. Required report data survived opening with python-docx and JSON/Markdown readers. DOCX author and last-modified-by fields, and PDF fixture author, were verified as Ethan. Original uploads are preserved byte-for-byte; their metadata is never rewritten. Finder/Windows shell metadata displays were not separately verified.

## Limitations

Pattern conditions cover narrow drafting forms. Negations, definitions, cross-references, unusual layouts, exceptions, and broader legal context may need manual review and can fall outside a rule's recognition. COMPLIANT means configured conditions matched, not that the agreement is legally sufficient. Governing-law guidance is configurable and illustrative.

OCR, encrypted PDFs, DOCX revisions/macros/text boxes/notes are unsupported. PDFs with textless pages are rejected. DOCX headers/footers are excluded with a visible warning. Verify full originals. This is a single-user loopback application without authentication or application-level encryption; not a public-hosting service. Deletion does not erase exports, backups, or guarantee SSD forensic erasure. The OpenRouter adapter, consent, budgets, and citation gates are implemented, but successful live AI interpretation remains unverified until CR-18 can run with authorized credentials.
