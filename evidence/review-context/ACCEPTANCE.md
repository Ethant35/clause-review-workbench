# Version 1.4.0 qualification

Author: Ethan. Tested October 27, 2026.

This release targets one trusted local contract reviewer on the tested macOS
27.2 arm64 system, with Chromium for browser checks. The app bundles Python3.12.14
and locked dependencies. The macOS13 deployment target is a loader minimum,
not a claim that older systems were tested.

## Behavior and evidence

Ordinary agreement durations and expiration are recognized separately from survival.
Conflicting terms and unsupported conditions remain unresolved. Multiple explicit
cap exclusions link to the base cap and supported separate limits; the result does
not assume that an exception makes the entire agreement uncapped. Saved policy
context returns with the review. Findings distinguish adverse wording, not-located
provisions and unresolved interpretation. The synthetic sample has four substantive
findings and no absence findings, with all eighteen commercial checks enabled.

| Check | Result |
| --- | --- |
| Final clean source archive | Frozen install, 152 Python tests and 10 subtests pass; six dependency warnings |
| Browser/API end-to-end | 18 pass; both optional provider tests blocked by default |
| Synthetic corpus | 12/12; zero observed fixture scoring/citation mismatches |
| Interaction fixtures | 98/98 |
| Adversarial fixtures | 83/83 |
| Sample workflow | 8 checks pass, including source, decision, export, returning history and PDF visual gate |
| Saved-policy browser | Restore saved NDA policy, new-run selection, historical snapshot/notes and priority/basis checks pass |
| Frontend readiness | 14/14, including keyboard flow, recovery, pagination and axe states |
| Actual Chromium zoom | 9/9 at 200%/400%; selected rendered screenshots inspected |
| Native app | Six launch, relocation, restart, data and recovery checks pass with system-only PATH |
| Prior releases | v1.2.0 and v1.3.0 source-created data imports pass; raw review JSON, original, policy and decisions preserved |
| Bundle identity | 66 source/doc/license hashes match; frontend and bootstrap bytes match; untracked duplicates excluded |
| Local quarantined DMG | Signature, tickets, Gatekeeper, AppTranslocation, browser journey and shutdown pass |

The initial accessibility run found low-contrast source-location labels. The color
was repaired and the full affected readiness/zoom checks passed. Independent source
review also found an omitted explicit "will not apply" cap-exception form; it was
repaired with positive, negative, narrow-exception and source-anchor controls.
The floor guard retains its general assertion-removal check with two exact reviewed
migrations and six positive/near-miss/removal tests. No tests were disabled to pass.

One final source-archive browser run lost its active browser page after a click
stability timeout, while its API-only checks still passed. The failure JSON and
logs are retained privately. An isolated rerun of the exact same archive and test
code passed all eighteen local checks without changing assertions or timeouts.
The root cause of the browser interruption is not established; the passing run
emitted macOS CVDisplayLink warnings. Installed-app browser acceptance also passed.

Results produced before the implementation commit record the preceding HEAD as a
baseline; this does not mean the checkout was unchanged. Bundle hashes and the
sealed archive identify the tested contents separately. The archive has Ethan
owner fields; bundle copyright and generated author fields identify Ethan. Upstream
notices remain intact. Screenshot author metadata was not verified.

## Distribution

Developer ID: Ethan Tarnarider, TeamZ2SL92S4B6. Apple accepted app submission
2ecb3433-ce20-4930-8ff5-a8359a68d6d1 and DMG submission
48d5b5ad-c993-48d7-941d-8d0d7b28eac8. Both have stapled tickets. The installed copy
passed deep strict codesign, Gatekeeper and syspolicy_check, then launched through
AppTranslocation. Source, finding decision, export, reload and shutdown passed.
Exact PyMuPDF/MuPDF corresponding sources accompany the release. Checksums are
in release-hashes.json. Publication and public-download acceptance are the remaining
gates at this pre-publication checkpoint; local acceptance alone is not public proof.

## Limits

These checks do not establish general legal accuracy, enforceability, complete
clause interaction reasoning, automatic extraction completeness, OCR, successful
live AI, other operating systems/browsers, VoiceOver or unfamiliar-user usability.
The unchanged public Common Paper documents test PDF layout, not representative
executed-contract accuracy. Extraction warnings and the manual PDF comparison
remain required. Source matching proves correspondence, not legal significance.

No live provider request ran in the October27 qualification. A prior October25
legacy test made one rejected invalid-key request; that led to the explicit opt-in
fix. No credentials or real contracts were sent in that test. Semgrep was not rerun;
its existing triage, timeouts and partial coverage remain disclosed in
../../docs/readiness-semgrep.md. No clean-security or penetration-test claim is made.
GitHub Actions remain disabled. All acceptance runs are local.
