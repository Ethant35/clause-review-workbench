# Terra review fixes verified — October 29, 2026

Author: Ethan. Branch: codex/terra-review-fixes.
Source candidate: cc50e1c3308830ceb615d94770c8d180e36bfbc9.
The user authorized fixes, independent Terra verification, then PR creation and merge.
The five observed issues are fixed: library identity, source-check readiness text,
DOCX export timestamps, singular retention wording, and missing-setup diagnostics.
Independent review also found repeated same-minute reprocessing ambiguity and a
390 px action overflow; both were repaired and rechecked. Original documents,
saved reviews, notes and decisions remain intact. Legal-analysis rules are unchanged.

Verification: 176 Python tests + 10 subtests, six dependency warnings; browser/API
18 pass and two provider checks blocked; usability and revision browser checks pass;
frontend readiness 14/14; intended-diff floor guard clean. Terra's final bounded
verdict is PASS. Details and exact candidate mapping: evidence/terra-fixes/verification.json.
Full local reports/screenshots: artifacts/terra-fixes-20261029/independent.
Initial failures and the intermediate REVISE verdict are retained there.

All computer use for these fixes stayed headless/background. No paid calls,
GitHub Actions, global configuration changes or production goal changes. All owned
test/reviewer servers are stopped. Both usage-based stops were explicitly disabled
by Ethan on October 29; do not revive the historical guards below.

This is a source PR, not a new packaged release. v1.5.0 installers and immutable
release tag remain unchanged. The source environment is restored locally (.venv
and frontend build); the isolated public app remains a separate older build.
Unrelated duplicate files, the broken main 2 ref and shared skill symlink remain.

---

# Version 1.5.0 complete — October 28, 2026

Author: Ethan.

Release: https://github.com/Ethant35/clause-review-workbench/releases/tag/v1.5.0
Merged PR: https://github.com/Ethant35/clause-review-workbench/pull/9
Immutable release tag: 3fc975abb5df6fff63794357b7ae1e58dc4a7af1.
Tested implementation/source candidate: 5f15a0723f1d2a890fef24ba5e568d6d06ff14f3.
Later evidence commits do not modify sealed assets or the release tag.

The app now compares clean contract revisions and saved reviews, shows exact
before/after text and supported related-clause effects, and flags prior decisions
for reconsideration after source, policy or check changes. Original documents,
notes and decisions remain in their original review. New reviews start unresolved.
Different check versions or policies are disclosed rather than attributed to edits.

Extraction revision 6 retains PDF coordinates and DOCX table-cell locations,
gates uncertain PDF layout/annotations and rejects unsupported DOCX content that
would be omitted. Old documents must be reprocessed into separate records; stored
historical reviews remain unchanged. No OCR or general redline parsing claim.

Independent-label evaluation covered all 102 CUAD test contracts and 408 category
observations with no recognizer tuning. It exposed material gaps: caps 22/44 and
convenience termination 11/29 located. External labels are independent, but the
adapter is implementation-authored. No independent lawyer has validated risk,
exception reasoning or revision effects. The human-review protocol is prepared,
not executed. See docs/legal-evaluation.md and evidence/revisions/cuad-evaluation.json.

Verification: 174 Python tests plus 10 subtests; browser/API 18 pass with both
provider tests blocked; corpus 12/12, interactions 98/98, adversarial 83/83;
frontend 14/14, zoom 9/9; revision browser, real v1.4 migration and legacy upgrade
checks pass. Full clean qualification passed. All 277 source archive files and
69 bundled source/docs/license hashes match the tested candidate; rebuilt frontend
and bootstrap match. Failures and repairs are retained in the acceptance record.

App and DMG received Apple Accepted, were stapled, and passed local and public
quarantined installation. All five public downloads match sealed hashes and GitHub
digests. Gatekeeper, syspolicy_check, AppTranslocation, installed revision workflow
and shutdown passed. Evidence: evidence/revisions/ACCEPTANCE.md and adjacent JSON.
Detailed local evidence: artifacts/revisions-20261028; public installed artifacts:
/private/tmp/crw-public-install-1.5.0-20261028. Sealed assets:
/private/tmp/crw-release-1.5.0-20261028. Prior releases remain unchanged.

No paid calls, Actions runs, new assistants, global configuration changes or new
security-scan claims. Actions are disabled. No owned app/server processes remained;
the process registry is empty. Final qualification usage: 42% used / 58% remaining,
reset_at 1793774143 unchanged. The updated stop condition is 50% REMAINING or an
observed reset to 100%, superseding older thresholds and the original goal text.
The delivery is complete; stop the monitor and complete the actual goal at closure.
No automatic continuation is authorized. Existing duplicate files, broken main 2
ref and shared skill symlink remain untouched.

---

# Version 1.4.0 complete — October 27, 2026

Author: Ethan.

Production release: https://github.com/Ethant35/clause-review-workbench/releases/tag/v1.4.0
PR #8 merged: https://github.com/Ethant35/clause-review-workbench/pull/8
Immutable tag commit: 03b6dbaed1fac5bc2cad833a20be0770d7bcf895.
Later commits add evidence only; sealed app/DMG/source bytes are unchanged.

Signed, Apple-notarized and stapled app/DMG passed local and public downloaded
quarantine, codesign, Gatekeeper, syspolicy_check, AppTranslocation, actual browser
sample/source/decision/export/reload and shutdown. All five public assets were
fetched without authentication and matched hashes. DMG SHA256:
023546384d2654992209f461834223d8737a6b8c4f8be3c27c3dfd5a53e7821c.
Source archive SHA256:
ba31694d8df8aae43b35c79bc62c3c4ac0a9263532bcb1f346cb1d3401e2bf0f.
Exact PyMuPDF/MuPDF sources and checksums accompany the release.

Final clean source: 152 Python tests +10 subtests; browser/API18 pass with both
provider tests blocked. Corpus12/12, interactions98/98, adversarial83/83,
frontend readiness14/14, zoom9/9, sample8 checks, saved policy context, native6
checks, v1.2.0/v1.3.0 original/review/policy/decision preservation all pass.
One source-browser interruption is retained and disclosed; an isolated unchanged
rerun passed. No test timeout or assertion was weakened to conceal it.
Independent review, targeted regression controls and clean intended-diff floor
checks passed. Narrow test migrations have exact paired guards and negative tests.

Evidence: evidence/review-context/ACCEPTANCE.md and adjacent curated JSON.
Detailed local runs: artifacts/verification-20261027. Final artifacts remain in
/private/tmp/crw-release-1.4.0-20261027; downloaded bytes in
/private/tmp/crw-public-1.4.0-20261027; installed public test data in
/private/tmp/crw-public-install-1.4.0-20261027. Preserve until no longer needed.
General legal accuracy, OCR, complete extraction, live AI success, VoiceOver,
other platforms/browsers and unfamiliar-user usability remain unqualified.
No further required implementation or release work remains for this stated scope.

Both assistants completed and were interrupted. All owned test/native processes
exited; ports closed. Process registry cleared. Checker cell3 terminated at close.
Actual account usage49%->74% used (51%->26% remaining), same reset_at1793599137;
no in-work reset or <=5% remaining trigger. No reset/credit/provider bypass.
No provider calls during this continuation. GitHub Actions disabled; zero runs.

Unrelated duplicate files, shared skills symlink and broken refs/heads/main 2 are
preserved. That pre-existing ref blocked a normal fetch. A clean temporary clone
fetched merged main, then git bundle unbundle supplied the verified commit; only
origin/main was advanced and local main fast-forwarded. No unrelated ref was edited.
No global config or hooks changed. No user data changed. Final goal completion
is recorded through the actual existing production goal, never a duplicate.
Earlier checkpoints below are historical and superseded by this completion record.

---

# Active production continuation — October 27, 2026

Author: Ethan.

Ethan explicitly resumed production work and restarted the actual broad goal;
get_goal now reports ACTIVE. No replacement goal was created. Current usage guard
supersedes ALL older thresholds below: stop at <=5% remaining (>=95% used) in any
applicable window, or an observed in-work reset to 100% remaining. Check actual
usage at least every60 seconds; retry unknown readings once, then stop if still
unknown. Startup baseline49% used/51% remaining, reset_at1793599137. No idle reset
was treated as an active reset. Lead checker cell3 reads every45 seconds.

Current candidate1.4.0 includes the saved term/cap/policy fixes plus explicit
will-not-apply cap exceptions, native v1.3.0 upgrade coverage, tracked-file native
inventory, source-location contrast repair and updated documentation. Full source
integration is underway in artifacts/verification-20261027. Source tests passed
before a narrow contrast repair; final accessibility/state/zoom and native/release
gates remain. No provider opt-in is enabled. GitHub Actions confirmed disabled.
Unrelated duplicate files and the shared skills symlink remain untouched.
This is a checkpoint, not a completed release. Earlier pause notes are historical.

---

# Pause-only goal audit — October 25, 2026

Author: Ethan.

Ethan manually changed the ACTUAL goal to the production-readiness objective.
get_goal confirmed status PAUSED. This supersedes the earlier objective-edit
limitation notes below; do not create a replacement goal. No product work resumed.

Actual objective (verbatim):
"Make Clause Review Workbench production-ready for its intended contract reviewers on supported macOS systems. Publish a signed, notarized, verified downloadable release with simple installation and onboarding, reliable document extraction, source-linked findings, clear distinctions between adverse language, missing provisions and unresolved interpretation, consistent playbook selection, saved decisions and notes, useful exports, recovery, accessibility, and update compatibility. Preserve original documents and historical review snapshots. Verify the packaged app and public download using realistic and adversarial synthetic documents; document legal-analysis limitations without claiming general legal accuracy. Optional AI requires explicit data-transmission and spending authorization. Retain evidence. Phase completion alone does not complete this goal. No GitHub Actions. During active work, check usage at least every 60 seconds; stop at 10% or less remaining in any applicable window or an observed reset to 100% remaining. On either trigger, stop owned workers/processes, save a handoff, and pause this goal. No automatic resume or usage bypass. Keep this goal paused until Ethan explicitly resumes it."

Both assistants are completed and were interrupted. Process inspection found no
owned app/test servers; the process registry is empty. Checker cell 4 already
completed and closed. No checker restart or release action occurred. Wait for
Ethan's explicit resume instruction.

---

# PAUSED: in-work usage reset — October 25, 2026

Author: Ethan.

## Mandatory stop checkpoint

Confirmed shutdown: goal tool returned PAUSED. Usage checker cell 4 completed and
was closed. No worker, test/server process, or automatic-resume operation remains.
Ethan's subsequent explicit STOP message confirms the same reset stop.
Branch: main. Uncommitted tracked changes: HANDOFF.md, README.md,
backend/workbench/engine.py, relations.py, safety.py, frontend/src/App.tsx,
frontend/src/styles.css, tests/e2e.py, tests/test_analysis_readiness.py and
tests/usability_frontend.py. Intended new untracked files: frontend/src/sample.ts,
tests/test_sample_workflow.py, tests/review_context_e2e.py, and the three files under
.agents/verify-clause-review-workbench (SKILL.md, feature-map.md, agents/openai.yaml).
Unrelated duplicate files remain untouched. No staging/commit/push was done.
Required user input: explicit instruction to resume after this stop; none otherwise.

Actual paused goal objective (verbatim):
"Inspect Clause Review Workbench using the pinned pstack practices and independent reviewer evidence; reproduce key recognition and saved-policy issues with isolated synthetic data; conduct grill-me rounds and obtain Ethan's confirmation of scope before implementation. Then implement only the confirmed scope, create and execute the project-local verification procedure, and complete appropriate local regression checks and review. Preserve existing releases, unrelated files, privacy, no-Actions rules and both usage stopping conditions."


The active usage checker observed 0% used / 100% remaining with reset_at
1793599137, after the current run's 22% reading at reset_at 1793514805.
This is an observed in-work reset and triggers Ethan's explicit stop condition.
No work may continue into that refreshed allowance. Both assistants were already
finished and interrupted. The last pytest process exited 0, the process registry
is empty, and a process inspection found no owned app/test servers running. The
checker loop ended on the stop. No automatic resume or reset redemption.

Current goal was active; pausing it at this checkpoint. Only create_goal,
get_goal and update_goal(status) are exposed. There is NO supported objective-edit
mechanism. The existing milestone is genuinely unfinished (final integrated E2E
and fresh-native procedure remain), so it must not be falsely completed/replaced.
Ethan expressly requests this actual next objective when a valid transition is
possible:

"Make Clause Review Workbench production-ready for its stated supported users and platform: publish a verified downloadable release with reliable installation, onboarding, first useful result, core workflows, error recovery, data persistence and update compatibility, appropriate accessibility and security, and truthful documentation and support limits."

This text is recorded, not claimed as the actual goal objective. The actual paused
objective remains the investigation/alignment/confirmed implementation/verification
milestone returned by get_goal. Explain this tool limitation honestly.

### Implemented, uncommitted

- engine.py: located ordinary expiry, written durations, sentence-scoped custom
  criteria, survival/negation/condition guards, conflicting duration/date checks,
  and narrowly permitted stated-base-term early termination qualifiers.
- relations.py: every supported same-block cap exception, inline exclusions,
  separate limits and category-specific suggested responses. Source anchors remain
  raw and exact. REVIEW_REVISION is 5; prior reviews are historical, not rewritten.
- App.tsx/styles.css: restored saved policy, distinct next-run policy, highest
  priority selection and adverse/not-located/unresolved finding basis.
- frontend/src/sample.ts: full synthetic commercial sample, 4 substantive findings
  and no absence findings in observed run; no policy checks disabled.
- New test_sample_workflow.py and review_context_e2e.py, expanded analysis tests.
- .agents/verify-clause-review-workbench/ is explicit-only and local, not installed
  through the shared skills symlink. Syntax validation passed; procedure is NOT
  fully executed yet because fresh native validation remains.
- tests/e2e.py now requires separate opt-in for BOTH provider rejection and live AI.
  Initial legacy test made one invalid-key synthetic provider call and was rejected;
  user informed. Subsequent runs must leave both opt-ins unset. README documents it.
- tests/usability_frontend.py saves sample screenshot and allows multiple source
  cards for real clause interactions; still verifies exact selected source text.

### Evidence and exact limits

artifacts/verification-20261025 contains:
- pytest-final.log: FINAL source 140 passed, 10 subtests, 6 dependency warnings.
- focused-final.log: earlier intermediate 48 passed; final worker focused 54 passed
  /10 subtests, independently followed by above full 140-test pass.
- interactions.json: 98/98; adversarial.json: 83/83. These precede the last bounded
  term-conflict/early-termination repair; rerun affected integrated suites.
- usability-final.log: 8 checks PASS at artifacts/usability-frontend-wp4doanw,
  with sample-review.png visually inspected, source/decision/export/reopen/settings,
  reprocessing and PDF visual-check gating. Also precedes final term repair.
- initial-e2e-results.json and initial-corpus-results.json preserve failed initial
  E2E evidence. Old corpus early-termination cases initially regressed to uncertain;
  the final bounded repair restores a definite base term but has NOT had complete
  API/browser E2E/corpus rerun. Do not report these paths passing yet.
- Focused policy browser pass at artifacts/review-context-dkrurrxo; screenshot
  inspected. Original snapshot, note, decision, JSON export and source verified.

No new native bundle, signed app, notarization submission, PR, commit, push or
release was made. Main remains current; unrelated duplicates/private branch were
preserved. GitHub Actions were freshly confirmed disabled. Public latest remains
v1.3.0. A warning mentions broken duplicate ref refs/heads/main 2; preserve it,
do not opportunistically delete unrelated synced artifacts.

### Resume order after new human authorization and fresh usage baseline

1. Read this checkpoint; do not repeat research/interview. Check actual goal/usage.
2. Rerun full E2E with provider flags unset, corpus, final interactions/adversarial,
   and focused context browser on stable current source. Investigate real failures.
   Check last conflict repair independently; prior reviewer found it, worker fixed
   it, full unit pass verified it, but no post-repair independent review yet.
3. Run the local verification skill through fresh native bundle + upgrade. Native
   harness currently hardcodes v1.2.0; add/select v1.3.0 baseline for current update
   proof while preserving existing support. Source build caches are present.
4. Broader production scope is authorized: remaining acceptance map below covers
   readiness/error/accessibility, source packaging/licenses, fresh signing/notary,
   verified public downloads and documentation. Build outside synced workspace.
5. Only after the current milestone is actually complete: complete it and create
   the EXACT broader goal above, unless an actual objective-edit mechanism becomes
   available. Do not call the whole app done merely for finishing this milestone.


Ethan confirmed the combined scope in this chat. Investigation is complete;
implementation and local verification are authorized. Ethan subsequently expanded
the objective to production readiness and downloadable distribution, including
normal repository/release work. The goal now reports ACTIVE with the original
confirmed implementation/verification milestone objective. No objective edit or
duplicate goal was made. At completion of that actual milestone, create the broader
production/distribution goal, without a token budget. Do not claim the broader
objective complete until public final bytes and supported user journeys match.

Scope: conservative term recognition (wording, conditions, negation, survival and
paragraph boundaries); distinguish adverse matches, not-located provisions and
unresolved interpretation; restore saved policy context while making next-run
changes explicit; separate guidance from recognition; useful full synthetic sample,
high-priority initial selection and exception-specific responses. Preserve source
anchors, saved policies/results, decisions, notes, exports and history.

Two reused Luna assistants own backend recognition/relations and frontend context.
Lead owns sample, local verification skill and integration evidence. No nested
agents, GitHub Actions, AI provider calls, global settings or external messages.
New release assets are authorized; sealed old assets must not change. Preserve all unrelated duplicate files.

Prior reproductions remain in artifacts/review-followup-20261024. Do not repeat the
interview or overwrite that evidence. The independent NDA is held-out source text,
not a general legal-accuracy benchmark. Local dependencies restored from existing
locks; no dependency versions changed. Verification entry point is the app-local
.agents/verify-clause-review-workbench/SKILL.md, outside the shared skills symlink.

Usage startup: 7% used / 93% remaining, reset_at 1793514805. This is a fresh baseline
after the idle interval; prior reset timestamp 1793385116 is not an in-work reset.
Check at least every 60 seconds while active. Stop at >=90% used in any applicable
window OR a reset observed during active work to 100% remaining. Unknown after retry
also stops work. Do not redeem resets or use credits/providers to bypass the guard.
At a stop, stop owned workers/processes, save evidence and handoff, pause the goal.

Production acceptance gaps, in priority order:
1. Close final code regressions and independently review meaningful changes.
2. Complete current source/browser/error/privacy/accessibility regression suite.
3. Package fresh version with source/licenses and exact dependency source assets.
4. Exercise fresh bundled launch/restart/recovery and update from v1.3.0 with data
   unchanged, plus native controls and uninstall/data-retention documentation.
5. Sign, obtain Apple's acceptance, staple and verify exact app/DMG bytes.
6. PR/local review, Actions-disabled checks, release, anonymous download/hash and
   quarantined clean-install workflow. Verify final public bytes and cleanup.
7. Save exact support/limits and evidence. Optional successful live AI, OCR, other
   operating systems and unfamiliar-user/VoiceOver research remain unqualified.
No user input needed currently. Live-provider testing would require separately
specified provider, synthetic payload and finite cost authorization.

Implementation/checks are in progress; do not treat this checkpoint as completion.
Initial legacy E2E CR19 made a synthetic invalid-credential provider request, which
was rejected. User was informed. Both provider tests now require explicit opt-in
and remain blocked in subsequent default local runs; do not repeat that request.

---

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
