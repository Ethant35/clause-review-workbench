# Revision comparison and source fidelity qualification

Author: Ethan. October 28, 2026.

Scope: checked source changes on `codex/revision-fidelity`, based on v1.4.0.
This record does not qualify a new signed Mac build, notarization or public
download. Published v1.4.0 assets are unchanged. No new legal recognition patterns
were tuned against the external test labels.

## Behavior checked

- Separate clean-version uploads retain original bytes and link to the earlier
  document. New reviews have fresh unresolved decisions and empty notes.
- Comparisons include exact before/after paragraphs and rule-level finding changes,
  including evidence from supported cap exceptions and separate limits.
- A change anywhere in source bytes, extracted text, saved policy or extraction/
  analysis revisions prompts reconsideration of prior recorded decisions. No
  decision transfer occurs, even for text-identical documents.
- Different saved policies or check versions are not attributed to contract edits.
  Same extracted text with different original bytes has an explicit warning.
- Hash mismatches, changed saved text, missing baselines and stale browser responses
  fail visibly without changing an earlier review. Deleting an earlier document
  does not cascade to later uploaded revisions.
- PDF line geometry catches side-by-side text inside a combined extraction block.
  Images, forms/annotations, uncertain reading order and exhausted layout checks
  block review pending source comparison. DOCX omissions are rejected; supported
  table paragraphs retain physical-cell locations. Extraction revision is 6.

## Local verification

The curated records beside this file contain local result reports and Python
result summaries with hashes of the unchanged raw logs. Raw dependency warning
output contains a third-party suppression token that the diff guard rejects;
that output is retained locally, not copied into the repository. No checker or
assertion was disabled.

| Check | Result |
| --- | --- |
| Full Python suite | 174 tests plus 10 subtests; six dependency warnings |
| Existing browser/API suite | 18 passed; both optional provider tests blocked |
| Existing synthetic corpus | 12 / 12 |
| Existing interaction suite | 98 / 98 |
| Existing adversarial suite | 83 / 83 |
| Revision browser journey | Upload, lineage, related-clause comparison, prior decisions, fresh decision, export, reload, delayed-response guard, missing baseline and zero outbound requests passed |
| Revision accessibility | No serious/critical axe violations; desktop and 400 px screenshots visually inspected |
| Existing frontend readiness | 14 / 14 |
| Actual Chromium 200% / 400% zoom | 9 / 9 |
| Real v1.4.0 database | Historical raw review and original bytes unchanged; old extraction blocked; reprocessing/new decisions/comparison passed |
| Real v1.0.0 upgrade | 7 / 7, including recovery, exports and browser behavior |
| Intended-diff floor guard | Clean isolated Git checkout, excluding unrelated pre-existing duplicate files |
| Dependency setup | Frozen uv sync, npm ci and frontend build passed; lockfiles unchanged |

The final source hash manifest is `source-hashes.json`. Most result reports record
the starting commit because the feature was uncommitted during execution; those
commit fields do not identify the tested final tree. This manifest and the PR diff
identify the source changes. Final source-confirmation wording was covered by the
Python intake/export and revision regressions.

Detailed evidence: `artifacts/revisions-20261028`, with isolated browser runs under
`artifacts/revision-e2e-*` and migration data under `artifacts/revision-upgrade-*`.
Original files and saved reviews used in these checks were synthetic.

## Failures retained and repaired

The first new PDF test exposed two columns combined in one block; line geometry
now triggers the source gate. The initial new comparison fixture used a narrow
fraud exception, which the existing policy intentionally treats differently from
a broad carveout. The main changed-finding fixture now compares indemnity with
confidentiality; the fraud variant is retained as a separate no-longer-flagged
control that still requires revisiting the prior decision.

Browser checks found low contrast in comparison help, ambiguous selector labels,
and a 720 px header overflow. These were repaired without weakening existing
assertions. Adding related-evidence disclosures required the new browser test to
target the parent summary explicitly. A legacy upgrade check exposed inconsistent
historical-warning prefixes; the product warning is now consistent. Initial logs
remain in the local evidence directory. Final checks above passed.

## Legal-quality evidence and limits

`cuad-evaluation.json` reports all 102 contracts in CUAD's public test split across
four mappings. All completed, with no omitted failures or recognizer tuning.
The benchmark found material detection gaps: 22/44 labeled cap contracts and
11/29 convenience-termination contracts were located by the mapped app rules.
Source evidence coverage is reported separately. Category scope differences and
all denominators are documented in `docs/legal-evaluation.md`.

The labels are externally authored under experienced lawyers' supervision. The
evaluation adapter and rubric mapping are implementation-authored. No independent
lawyer has validated this app's risk judgments, cross-clause reasoning or revision
effects. The prepared independent legal-review protocol has not been executed.
Software test success must not be represented as legal validation.

No paid provider calls, no GitHub Actions, no subagents, no global config changes,
and no new security-scan or release-readiness claim. Source documents and generated
JSON/fixture DOCX personal author metadata use Ethan. Synthetic screenshot personal
author metadata was not controlled or verified.
