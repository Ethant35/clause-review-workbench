# Local deployment qualification

Author: Ethan. Version 1.2.0. October 22, 2026. Published and download-verified.

The complete clean-checkout qualification passed at commit
`0ea413aff05c74e31a75951eb4c348cccefed2c5`. The archive from source commit `332aa0383033bea2e6bdbd282551efcc3e5fe8f5`
passed fresh-install browser checks and packaged doctor/backup/restore. Its 122
tracked source files match Git; runtime, build and test files are byte-identical to
the clean-tested commit. See `evidence/readiness/package-verification.json`.
The supported target is one trusted user on macOS 27.2 arm64, Python 3.12.14,
Node 22.13.1 for builds, and Playwright Chromium. The operating-system account and
private directory form the trust boundary. There is no hosted authentication,
tenancy or network-service availability claim.

| Area | Verified evidence | Limit |
| --- | --- | --- |
| Core workflow | Real upload, review, decisions, notes, snapshots, exports and retention; 20 E2E passes including fresh installation | CR-18 successful live AI blocked |
| Clause/extraction | 83 adversarial, 98 interaction, 12 synthetic corpus scenarios; 24 focused analysis tests and 260 property examples | Independent fixture expectations, not general legal-accuracy measurement |
| Storage and recovery | SQLite-full rollback, concurrent partial edits, interrupted deletion, corruption, manifest and destination races | Same-user cooperating processes; no hostile-host/power-loss guarantee |
| Prior data | Seven real-server backup/restore/upgrade checks each from v1.0.0, v1.0.1 and v1.1.0 | Preserves snapshots/decisions/originals; older results remain historical |
| Boundaries and AI faults | Request-size/time/admission controls, malformed and slow provider payloads, cancellation and restart | Controlled HTTPX fault/success responses are protocol tests, not live-provider proof |
| Interface | 14 frontend checks, actual late-response/export test, modal keyboard/error test, nine 200%/400% zoom checks | Chromium only; axe tested states, not full WCAG or screen-reader certification |
| Performance | 37,440 real HTTP requests over 180 seconds, eight concurrent clients, 1,001 history rows; p95 24.10 ms, p99 46.70 ms | Bounded workload; endpoint RSS 66,768 to 69,488 KiB does not prove no leaks |
| Diagnostics/startup | Private 1 MB JSON log plus two backups; nine startup failure/actual HTTP tests | Content-free operational data only; no cloud telemetry |
| Security/dependencies | Differential review, nine approved Semgrep scans with individual triage; npm/Python audits have no known advisories | Partial rules/taint timeouts/test exclusions disclosed; no security certification |
| Release | Versioned notices, startup/recovery/rollback instructions, clean script and archive smoke | Clean checkout and archive installation/recovery passed; public download SHA-256 matched the tested archive |

The full Python suite now contains 87 tests plus two subtests, including ten floor
guard mutation/replacement controls. A passing test count is not a legal score.
Detailed supporting records: [analysis](readiness-analysis.md),
[frontend](readiness-frontend.md), [security](readiness-review.md),
[Semgrep](readiness-semgrep.md), [skill use](readiness-skills.md),
[startup](startup.md), [recovery](recovery.md), and
[dependency licenses](../THIRD_PARTY_NOTICES.md).

## Decisions and safeguards

SQLite commits logical deletion and a durable pending-deletion row before source
unlink. Cleanup retries after interruption. Connections close explicitly. Partial
PATCH merges only supplied nonnull fields; AI updates re-read the latest row.
The browser loads bounded pages and discards late responses after a new selection.

Recovery holds the same exclusive advisory lock as the app, validates original
hashes and SQLite consistency, stages a private copy, and atomically publishes into
a new destination. A pre-update backup and separate old application provide the
rollback path. Independent backups and exported copies are outside app deletion.

Diagnostics answer which route/status failed and how long it took, without source
text, filenames, document IDs, credentials, raw URLs or provider payloads. Normal
startup uses the installed environment and performs no dependency download.

## Experimental and unsupported behavior

AI assistance is opt-in and experimental. CR-18 remains BLOCKED_EXTERNAL because
an authorized successful provider/model configuration is unavailable. CR-19 tests
real authentication failure with an intentionally invalid credential. Controlled
provider tests establish bounded/error behavior only. No fallback or automatic
retry is made after an unknown outcome; a provider charge may have occurred.

General legal accuracy, unseen clause/exception grammar, automatic legal decisions,
OCR, complete PDF visual ordering, unsupported DOCX regions, hostile same-user
processes, hosted users, Linux/Windows, other browsers and VoiceOver are unqualified.
Exact quotes establish source correspondence, not correct legal interpretation.
Originals and excluded document regions still need human review. The application
as a whole is not labeled production-ready for autonomous legal analysis.

The clean run also repeated a 15-second, 3,600-request load check (p95 19.56ms).
The earlier 180-second run remains separate evidence. Full raw logs and browser
images remain in the ignored local run directory; selected reports and runtime
source hashes are in [evidence/readiness](../evidence/readiness/).

Publication: [v1.2.0](https://github.com/Ethant35/clause-review-workbench/releases/tag/v1.2.0),
[PR6](https://github.com/Ethant35/clause-review-workbench/pull/6). GitHub Actions
remained disabled with zero runs. Archive/report personal metadata identifies
Ethan; upstream notices retain their authors. Browser PNG personal-author metadata
was not configured or verified; their JSON evidence reports identify Ethan.
