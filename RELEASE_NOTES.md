# 1.5.1 — bounded review-assistance release

Author: Ethan. October 29, 2026.

Includes the merged UX fixes: distinct document references, source-check readiness,
truthful DOCX timestamps, retention wording, startup diagnostics and narrow buttons.
The commercial policy 1.0.1 repairs explicit without-cause termination detection
and longer monetary-cap wording. Negated/conditional termination rights cannot
satisfy the unrestricted-right check. Analysis revision is 6; extraction remains 6.
On upgrade the corrected policy is added separately. Select version 1.0.1 for new
reviews; saved/custom policies, decisions and historical snapshots are preserved.

Supported formats and 18 commercial / 6 NDA categories are frozen in
evaluation/release-contract.json. The legal-review packet separates extraction,
detection and interpretation and reserves four cases from project tuning.
Independent qualified legal acceptance remains pending. Known benchmark coverage
gaps remain; no general legal-accuracy, OCR or complete accessibility claim.

Software qualification and exact download hashes are recorded in evidence/release-1.5.1.
This section is a source description until public installed acceptance is recorded.

---

# Version 1.4.0 — contract interactions and saved review context


## 1.5.0 — October 28, 2026

- Upload a clean revision as a separate original; compare saved reviews, exact text
  changes, supported clause interactions and prior decisions. New reviews never
  inherit decisions or notes. Changed source, policy or check versions prompt
  reconsideration, including apparently unchanged findings.
- Keep PDF coordinates and DOCX table-cell locations. Check PDF reading order and
  annotations before review; reject DOCX numbering or non-body content that would
  be omitted. Reprocess older uploads into new records to use extraction revision 6.
- Export comparison JSON with saved policy contexts, original hashes, source
  changes, findings and earlier decisions. Historical reviews remain unchanged.
- External CUAD test labels expose detection gaps: the mapped rules located
  language in 22/44 cap-labeled and 11/29 convenience-termination contracts. This
  measures limited clause detection, not legal correctness. The rule view says
  “Configured conditions matched”; no independent lawyer validation is claimed.

Qualification and limits: [revision evidence](evidence/revisions/ACCEPTANCE.md),
[external-label evaluation](docs/legal-evaluation.md). Resolve tracked changes
before uploading; comparing clean versions does not interpret a marked-up redline.


Author: Ethan.

- Recognize ordinary agreement expiry and written durations separately from
  confidentiality survival. Conflicting dates, conditional wording and unsupported
  qualifications remain review questions. Narrow early-termination wording does
  not erase an otherwise definite base term.
- Link multiple explicit liability-cap exceptions, including indemnification,
  to the base cap and any supported separate limit. A cap exclusion alone does
  not establish unlimited exposure. Read all linked passages and conditions.
- Restore the saved review's playbook on return. Show the saved policy separately
  from the policy selected for the next review. Start at the highest-priority
  finding and distinguish adverse wording, missing provisions and unresolved meaning.
- Replace the short sample with a complete synthetic workflow example. It illustrates
  amendment risk, termination costs and category-specific liability limits.
- Review revision is 5; extraction revision remains 5. Earlier reviews keep their
  policy snapshots, decisions and notes and display a historical warning. A new
  review starts without copied decisions. Reprocessing still creates a separate
  document and preserves its original.
- Both optional provider tests now require explicit opt-in; local acceptance sends
  no provider request by default.

Quit and back up before replacing the app. Keep the old app and backup for rollback.
See [Mac installation, updates and removal](docs/macos-distribution.md). The supported
scope remains one trusted local reviewer on the tested Apple Silicon Mac. The checks
are bounded patterns; they do not establish general legal accuracy, OCR, successful
live AI, VoiceOver or unfamiliar-user usability. See the [release qualification record](evidence/review-context/ACCEPTANCE.md)
for the exact tests and downloadable-byte verification.

---

# Version 1.3.0 — Mac app and practical review workflow

Author: Ethan.

- Apple Silicon DMG with bundled CPython and locked dependencies. Native start,
  restart, backup, restore and prior-data import controls; no setup tools needed.
- Developer ID signing, Apple notarization and stapling for app and disk image.
- Short first-task flow, explicit Confirm finding / Dismiss finding decisions,
  source navigation, export and returning review history.
- Common playbook settings with stale-edit protection; advanced YAML remains
  available. Switching modes warns before discarding edits.
- Optional AI is collapsed by default. The native launcher stores an optional
  API key in Keychain. Consent, provider selection and budgets remain per request.
- Text PDFs with ordinary raster artwork enter an explicit manual completeness
  check. Scanned/textless/page-scale-image PDFs remain unsupported; no OCR claim.
- Reprocessing creates a new document from the hash-verified stored original,
  preserving old results and decisions. Extraction revision is now 5.

Before updating, quit the workbench and back up. Replace the app, leaving the data
folder intact. Source/tar users can import their stopped `.data` folder through
the launcher. Restore writes a separate data folder; it does not overwrite data.
Keep the old app and backup for rollback. See docs/macos-distribution.md.

The tested platform is macOS 27.2 on Apple Silicon. Broad legal accuracy, live-AI
success, OCR, other operating systems, and unfamiliar-user usability are not
qualified. See docs/usability-release.md for evidence and limits. PyMuPDF/MuPDF
AGPL notices and exact corresponding source downloads accompany the distribution.

---

# Version 1.2.0: safer local review and recovery

Author: Ethan

This release improves the single-user local workflow. It does not certify general
contract-analysis accuracy. AI assistance remains experimental; successful live
provider operation is still externally blocked in the qualification run.

- Detect more explicit liability-cap exclusions across paragraphs. Preserve
  negative and narrow-exception controls and exact related source evidence.
- Reject hidden DOCX text inherited from styles or defaults. Warn about comments,
  PDF annotations/forms and uncertain side-by-side PDF reading order.
- Preserve originals when database deletion rolls back. Retry interrupted source
  cleanup; close database connections; preserve fields in partial reviewer edits.
- Add private backup, restore and doctor commands. Recovery publishes only into a
  new directory and checks database consistency and original hashes.
- Bound library/history payloads, concurrent work, body reads and AI response time
  and size. Persist AI attempt consent and unknown outcomes without automatic retry.
- Add a skippable/replayable first-run guide, real synthetic example, keyboard tabs,
  modal focus handling, clearer contrast and protection from stale review responses.
- Start from an installed environment without downloading packages. Report safe
  startup errors and rotate private local diagnostics. Include dependency notices.

## Install or update

Use Python 3.12 and the locked dependencies. A source checkout also needs Node 22
for the frontend build; the release archive contains the built frontend. Follow
[startup](docs/startup.md). Normal startup is `./scripts/start.sh`.

Before updating, stop the old app and back up its data with the new release's
[recovery command](docs/recovery.md) into a new directory. Keep the old application
and untouched backup. Start 1.2.0 with the existing data path only after backup
verification. The schema additions retain previous records. Older extraction or
review revisions are labeled historical: re-upload the original and run a fresh
review for current checks; historical decisions and snapshots remain available.

To roll back, stop 1.2.0, restore the pre-update backup to another new directory,
verify it with doctor, and start the previous application against that restored
path. Do not run two versions on one directory or overwrite the only copy. Edits
made after the backup are not merged into a rollback copy. The tested forward
upgrades use real v1.0.0, v1.0.1 and v1.1.0 servers and backup/restore; this is not
proof of every downgrade or filesystem failure scenario.

## Evidence and limits

See the [qualification record](docs/readiness.md), [security review](docs/readiness-review.md)
and [third-party notices](THIRD_PARTY_NOTICES.md). The tested target is macOS arm64,
Python 3.12 and Chromium. Other platforms/browsers, VoiceOver, OCR, hosted users,
indefinite load and broad legal reliability remain unqualified. Exact quotes prove
source correspondence; a person must still assess their legal significance and
review source regions the extractor does not analyze.
