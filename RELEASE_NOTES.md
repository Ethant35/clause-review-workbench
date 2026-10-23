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
