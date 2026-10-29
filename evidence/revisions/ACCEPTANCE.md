# Revision comparison and source fidelity qualification

Author: Ethan. October 28, 2026.

Scope: version 1.5.0 candidate based on v1.4.0. The signed app and DMG received
independent Apple Accepted submissions and were stapled/validated. Local quarantined
installation passed strict codesign, Gatekeeper, syspolicy_check, AppTranslocation,
the original workflow and the new revision journey. Public download and installed
verification also passed, as recorded in the release section below.
No new legal recognition patterns were tuned against the external test labels.

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
and no new security-scan claim. Release qualification is recorded below. Source documents and generated
JSON/fixture DOCX personal author metadata use Ethan. Synthetic screenshot personal
author metadata was not controlled or verified.

## Packaged 1.5.0 candidate

Implementation/source candidate commit: 5f15a07 (full SHA recorded in Git).
Final source archive matches all 277 tracked file contents in the tested clean
checkout. A later evidence-only commit may add qualification without changing
these sealed bytes. The source archive was resealed only to update the clean
qualification harness baseline; runtime bytes and the signed app were unchanged.

The archive's plain, Git-free Python suite passed 174 tests + 10 subtests. The
adversarial harness completed its cases but could not write its Git commit metadata
without `.git`; the failure is retained in clean-adversarial.log. The exact public
candidate commit was then fetched into that clean directory, with zero source
diff, and the remaining integration suites were run against those same bytes.

The all-in-one clean qualification script initially used v1.1.0 as its floor
baseline; that historic cumulative diff exceeded the command output buffer.
The script now compares new work with the current qualified v1.4.0 release.
No floor rule or assertion changed. This diff is 435,238 bytes and the guard passed.
The clean script is rerun with the actual release tags in the isolated clone.

The release build manifest supersedes the earlier feature-stage source-hashes.json
for the packaged candidate. All 69 bundled source/docs/license hashes match source;
the independently rebuilt frontend and native bootstrap match. ZIP extraction
retained the accepted app ticket and valid deep signature. Native launch/recovery
and bundled v1.4.0 upgrade checks passed. No old release asset was modified.

App submission: 7bdf1406-9a99-4cfe-9ddd-76882e43629e.
DMG submission: f9a012dc-0c87-4b8d-8ac3-d8f0f701a309.
Apple returned Accepted and no issues for the app. The local installation report
and release-hashes.json identify the sealed DMG/source/component bytes.

Full clean qualification completed at commit 5f15a0723f1d2a890fef24ba5e568d6d06ff14f3.
The actual scripts/clean_acceptance.sh passed in a fresh Git clone with released
baseline tags. The final source archive contains the same source and harness.
See clean-qualification.json and clean-full-e2e.json. Optional provider checks
remained blocked; no provider request was made. Publication/public-download
verification follows these completed local gates.

## Public release qualification

Version 1.5.0 is published at
https://github.com/Ethant35/clause-review-workbench/releases/tag/v1.5.0.
PR #9 merged. The immutable tag points to
3fc975abb5df6fff63794357b7ae1e58dc4a7af1. This later evidence-only update does not
change the sealed assets or tag.

All five public assets were downloaded without authentication. Their byte sizes
and SHA256 values match the sealed local files and GitHub asset digests; every
entry in SHA256SUMS.txt was independently checked. See public-download.json.
The public DMG SHA256 is
884ea4fa6b31522ad4dec94b86289610d10aba3baf15596d5fdeec301652f797.

The downloaded DMG and copied app retained quarantine. Stapled tickets, strict
signatures, Gatekeeper and syspolicy_check passed. LaunchServices started the app
through AppTranslocation with isolated test data. The actual installed browser
journey passed sample upload, source navigation, decision, export and reload, then
revision upload, comparison export, fresh decisions and unchanged earlier decisions.
The final Revisions screenshot was visually inspected. Native exit closed the
server and port. See public-installed.json and public-installed-browser.json.
Detailed files remain under /private/tmp/crw-public-install-1.5.0-20261028.

The source implementation and evidence commits use Ethan as author; the native
personal copyright and JSON report author fields were checked. GitHub's merge
commit retains its factual account/platform attribution. Screenshot personal
metadata was not controlled or verified.

GitHub Actions remained disabled with zero runs. No paid provider call was made.
At final qualification, the allowance was 42% used / 58% remaining, with unchanged
reset time 1793774143. The updated 50%-remaining stop guard did not trigger.
No owned app/server process remained and the test process registry was empty.
This release does not establish independent lawyer validation, OCR support,
VoiceOver acceptance, unfamiliar-user acceptance or other-platform qualification.
