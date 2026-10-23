# Clause Review Workbench 1.3.0 — completed

Author: Ethan. Completed October 23, 2026.

Release: https://github.com/Ethant35/clause-review-workbench/releases/tag/v1.3.0
PR 7: https://github.com/Ethant35/clause-review-workbench/pull/7 (merged).
Tag commit: e1fa5dcad0e1e5be0571f755006fa0abc6c6b19b.
Packaged and clean-tested source: d36bdd71243860aefda8b0197cbd09a96ebf25c0.
Subsequent commits contain documentation/evidence only. All final backend,
frontend, native and build source hashes match the tested records.

## Published downloads

Signed, Apple-notarized and stapled Apple Silicon DMG:
012d862cdbb074ec79f507375d3f501210f8298553bf109da2c7b2cd27881e59
Workbench source archive:
fef32506633b9a0eb71c5fbdf863485deca8e3236f0995d48861bd35b420db46
Exact PyMuPDF and MuPDF sources accompany the release, with SHA256SUMS.txt.
All five public assets were downloaded without authentication and verified.
The public DMG was installed into a fresh test Applications directory, quarantined,
and launched through LaunchServices with AppTranslocation. Gatekeeper, native UI,
source/decision/export/returning browser journey and shutdown passed.

## Qualification

109 Python tests plus 2 subtests passed in the workspace and clean source install;
19 browser E2E passes with CR-18 successful live AI externally blocked; 98
interactions; 83 adversarial; 12 synthetic corpus; 14 frontend readiness; 9 actual
browser zoom checks. Bundled install/recovery journey 6 checks, real v1.2.0 import
4 checks. Native Keychain test used a unique disposable service, removed afterward.
Native build, signing, notarization, source comparison and public download evidence
are in docs/usability-release.md and evidence/usability/.

The app bundles its runtime. PDFs with small raster images require an explicit
manual completeness check. Scans/OCR remain unsupported. Reprocessing creates new
records and preserves earlier history. Common playbook settings preserve patterns
and reject stale edits. Optional AI retains consent and budget controls.

Qualified scope: one trusted local user on macOS 27.2 arm64 and Chromium. No claim
of general legal accuracy, successful live AI, automated extraction completeness,
other operating systems/browsers, VoiceOver or unfamiliar-user usability. Public
Common Paper templates are attributed layout fixtures, not accuracy benchmarks.
No private AstraforLaw access or private index was obtained; RESEARCH.md contains
earlier public research. Prior Semgrep qualifications remain in readiness records;
no new scan ran during this phase. No Actions workflows or runs were used.

## Cleanup and continuation

Both usability workers stopped. Test apps stopped, ports closed, test DMGs detached,
and process registry empty. The session monitor is terminated at completion.
Latest account usage: 79% used. If separately authorized work continues, stop at
90% used in any applicable window; unknown is not allowance. No reset/credit bypass.
No persistent automation or global config change was made.

Preserve 38 unrelated untracked files with ` 2` suffixes and private local branch
codex/readiness-local-evidence. Never push its raw scan history. Main contains only
intended source and curated evidence. GitHub Actions remains disabled with zero
runs; check before any later push/release/merge. No messages were sent to another
chat. Previous release records remain in Git history and evidence/readiness/.
