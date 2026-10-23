# Version 1.3.0 qualification

Author: Ethan. Tested October 22–23, 2026.

This release supplies a self-contained Apple Silicon Mac app and improves the
local review workflow. It is qualified for one trusted local user on the tested
macOS 27.2 arm64 machine. The native deployment target is macOS 13; that loader
minimum does not establish compatibility testing on older releases.

## Behavior

The sample leads through an actual review, an exact source passage, a finding
decision, export and a returning visit. Confirm finding and Dismiss finding record
the reviewer's disposition of the issue. They do not approve or change contract
terms. Common playbook controls preserve matching expressions and reject stale
edits. Advanced YAML remains available with an unsaved-change warning.

PDFs with small raster artwork require an explicit comparison against the stored
original. The acknowledgment binds the original, extraction revision and image
manifest. Review and AI remain blocked until it is supplied. This is a manual
completeness check, not OCR or proof of complete extraction. Textless pages,
page-scale scans and unsupported image geometry are rejected. Crop-edge artwork
receives an explicit warning. Reprocessing verifies the stored original and
creates a new document; earlier results, notes and decisions remain intact.

The native launcher bundles Python and the built frontend. Data lives outside the
app. Backup, restore and prior-data import use verified copies and new destinations.
The optional AI key uses Keychain; local review requires no key. Consent and
request budgets remain explicit. Recovery processes do not receive the key.

## Evidence

Curated results are in `evidence/usability/`. Tests ran on the final working tree;
pre-commit result fields identify its baseline commit, not an unchanged checkout.
The bundle source hashes are compared against the final source separately.

| Check | Result |
| --- | --- |
| Python | 109 tests and 2 subtests passed; 6 dependency deprecation warnings |
| Frontend production build | Passed |
| Browser end-to-end | 19 passed; CR-18 successful live AI blocked externally |
| Interaction suite | 98/98 |
| Adversarial fixtures | 83/83 |
| Synthetic corpus | 12/12; no observed fixture false positives, false negatives or citation mismatches |
| Frontend readiness | 14/14 |
| Actual browser 200%/400% zoom | 9/9 |
| Bundled app journey | 6 checks passed, including system-only PATH, restart and offline recovery |
| Actual v1.2.0 import | 4 checks passed; old data unchanged, history retained, explicit reprocess |
| Installed local DMG browser journey | Sample, source, decision, export and returning review passed |

Native Keychain create/read/update/delete used a unique disposable service and
passed; no saved user key was modified. The hidden AppKit harness exercised
readiness, restart, backup and shutdown. Actual native window inspection through
macOS accessibility and a rendered screenshot found readable named controls and
working restart/quit. An offscreen AppKit PNG had blank button labels and is
excluded from visual evidence. Automated checks are not an unfamiliar-user study.

Two unchanged, attributed Common Paper templates exercise real PDF layout and
crop-edge artwork. They are licensed public templates, not a representative
executed-contract dataset or legal-accuracy benchmark.

## Signing and installation

Developer ID: Ethan Tarnarider, Team Z2SL92S4B6. Apple accepted app submission
`58428a28-f8a4-4f5f-8d73-d82110cc3684` and DMG submission
`bb494909-2135-49d8-b403-788f8f6f0f24`. Both were stapled and validated. Deep strict
code verification and Gatekeeper assessment passed. The final stapled DMG SHA256 is
`012d862cdbb074ec79f507375d3f501210f8298553bf109da2c7b2cd27881e59`.

The local DMG was mounted, copied to a separate Applications test directory,
quarantined and launched through LaunchServices. macOS translocated the app and
it served the working interface. No Gatekeeper bypass or quarantine removal was
used. Public download acceptance is recorded separately after publication.

Early signing attempts inside the synced workspace failed because a file provider
added Finder metadata. Building in a new directory under `/private/tmp` resolved
the failure. The failed attempts were not published.

Exact PyMuPDF and MuPDF corresponding source archives accompany the release.
Upstream license text and original author notices remain intact. Source archive
owner fields, generated JSON author fields and controlled native bundle copyright
identify Ethan. Screenshot author metadata is not verified. Original Common Paper
document metadata is preserved rather than relabeled.

## Limits

These checks do not establish general legal accuracy, successful live-provider
analysis, OCR, automatic extraction completeness, other operating systems or
browsers, VoiceOver behavior, unfamiliar-user usability, or hostile same-user
isolation. Clause interaction checks remain bounded patterns with evidence and
uncertainty, not complete legal interpretation. No private AstraforLaw access or
private index was obtained. Earlier public workflow research remains in RESEARCH.md.

No new Semgrep scan was run in this phase. The prior approved scan's qualifications
remain in the readiness record. No GitHub Actions workflow or run was used.
