# v1.2.0 differential review

Author: Ethan. Review date: October 22, 2026. Baseline: release v1.1.0,
`4be65b4dd9915853e62d0ef709b112d4a4bb441a`. Scope: that release through
`cce30e4` plus the current readiness changes, including new untracked modules.
Unexpected local files with ` 2` suffixes were preserved and excluded from release.

## Decision and severity

Recommendation: conditional release of the supported local workflow after clean
checkout and packaged-install gates pass. Overall residual risk: medium. No
unresolved critical/high defect was confirmed in the reviewed application code.
This is a source review and bounded test result, not a penetration-test certificate
or evidence of general legal accuracy. Live AI, untested platforms and broader
extraction/interpretation remain outside qualification.

| Confirmed defect family, fixed | Severity | Verification |
| --- | --- | --- |
| Original unlinked before database commit; rollback could lose it | High | Real SQLite-full rollback, interrupted cleanup and restart tests |
| Hidden DOCX styles/defaults entered visible analysis | High | Real generated DOCX variants, default and inherited styles |
| Concurrent partial edits and late frontend responses could lose/display wrong state | Medium | Concurrent SQLite edits; held real browser responses and export identity |
| Unbounded list payloads and incomplete resource/AI deadlines | Medium | Bounded pages, admission/body timeout, slow provider stream and load tests |
| Backup publication race, corrupt saved shapes and fresh-directory startup regression | Medium | Real destination race, corruption fixtures, fresh startup |
| Modal focus/escape and unassociated YAML field error | Medium | Real browser focus containment, Escape and return-focus checks |

Severity describes the original consequences in a trusted local-user deployment.
It does not label heuristic scanner matches as confirmed vulnerabilities.

## Changed paths and attack surface

The lead read the current production paths below in full, plus changed lines
against v1.1.0. Dependency internals were not audited. Worker review and the listed
focused regressions supplement the lead review; no line-coverage percentage was
measured or inferred.

| Paths | Inputs/state/calls | Principal checks |
| --- | --- | --- |
| `backend/workbench/main.py`, `models.py` | Local HTTP bodies, IDs, multipart, YAML, query pagination; SQLite; provider consent | Parameter binding, schema bounds, Host/Origin, body deadline, admission, partial edits, AI audit transition |
| `store.py`, `recovery.py` | Private directory, SQLite, source UUIDs, manifests, CLI paths | Transactions, lock, rollback, pending deletion, no-overwrite publication, hashes, corruption, symlink refusal |
| `ai.py` | Explicit provider/model/budget, contract/playbook, external response | No fallback/retry, finite prices, output size, total deadline, reference shape and exact quote checks; controlled-fault evidence only |
| `parsing.py`, `parser_worker.py`, `relations.py`, `engine.py`, `safety.py`, `reports.py` | Document bytes/blocks, configured rules, historical review JSON | Parser process limits, inherited hidden styles, warning regions, capped PDF comparisons, negation/scope and exact anchors; escaped report data |
| `diagnostics.py`, `launcher.py`, `scripts/start.sh` | Route templates, status, environment, assets, loopback socket | No payload/raw path logging; bounded rotation; private directory; startup failure redaction; no normal-start install |
| `frontend/src/App.tsx`, `styles.css` | Local API replies, selections, reviewer text, consent, local-storage dismissal flag | Plain React text, stale request guards, partial payloads, pagination, keyboard/focus, contrast and real browser zoom |
| `tests/serve_checked.py`, `scripts/deployment_smoke.py`, `scripts/floor-guard.mjs` | Synthetic local fixtures, known release archive, local Git commands | Test-only held real responses; `tarfile` data filter; fixed subprocess argument arrays and mutation controls |

The lead also reviewed the new analysis, AI, boundary, storage, recovery, launcher,
floor, state and load test logic; workers reviewed browser-readiness/zoom and clean
acceptance harnesses. Build manifests and lockfiles were checked for the intended
test dependencies/version changes. New documentation and upstream license copies
have no runtime input surface. Historical publication evidence was retained.

## Checklist results

| Review item | Finding |
| --- | --- |
| SQL/command/template/header injection | SQL values parameterized; dynamic table limited to allowlist. No application shell interpolation. React renders plain text. Export format allowlisted; successful IDs identify stored UUID rows. |
| Authentication, authorization, sessions | No hosted user/session model. One trusted OS account and private directory is the declared boundary. Host/Origin checks are retained; loopback alone is not claimed as multi-user authentication. |
| CSRF and browser origins | Existing non-local Host/Origin rejection retained and exercised. Browser has no server credential cookie. No wildcard cross-origin policy added. |
| Races/state | Partial PATCH and AI updates read latest row inside write transaction. Pending deletion commits before unlink. Recovery/app share lock; final publication refuses an existing target atomically. Frontend sequence guards reject late results. |
| Crypto/secrets | SHA-256 is used for integrity, not secrecy/authentication; UUIDs name records. Key remains server-side and is excluded from diagnostics. No new home-grown cryptography. |
| Disclosure | Stable validation/storage errors and content-free route diagnostics. Startup tracebacks removed on supported launcher. Same-user private backup and local exports deliberately contain data. |
| Resource exhaustion | Size/block/regex/parser limits retained; list bounds, 30-second body budget, request groups, 120-second AI total budget and 1 MB response cap added. Short load evidence does not prove indefinite availability. |
| Business logic | Independent clause/exception/negative controls, historical 4/4 revision check, source exactness, reviewer-note integrity. Synthetic expected outcomes do not establish legal correctness across unseen contracts. |

## Blast radius and history

AST enumeration of production Python call sites (excluding tests and unexpected
copies) found: `db` 14; `review_view` 7; `exclusive_store` 4; `update_ai` 4;
`delete_document` 2; `assist` 1; `extract` 1. These are lexical direct call sites,
not a dynamic call graph. All requests and recovery operations depend on the
storage/lifecycle changes, so clean-install and prior-version stores are release
gates. The HTTP route reaches extraction through a subprocess; its one direct
call does not imply low user impact.

`git blame v1.1.0 -- backend/workbench/store.py` attributes the original SQLite
context and unlink-before-commit path to `a314ee8` (October 22, 2026). The change
preserves transactional foreign keys and secure-delete settings, closes the
connection explicitly, and adds a durable cleanup intent. No security check was
removed to pass tests. The only full-suite expectation adjustment selects the
specific saved-update live region after accessibility work introduced additional
status regions; it retains visibility, persisted-note and reviewer-decision checks.
The before-fix failure is retained in local evidence.

## Verification and limits

87 Python tests and two subtests passed in the working tree. This includes 260
Hypothesis examples, independent negative/positive controls, rollback/cancellation,
corrupt manifests, destination races and startup cases. Browser state checks passed
against real API responses. A three-minute 37,440-request local load run at eight
concurrent clients measured p95 24.10 ms and p99 46.70 ms; RSS samples were 66,768
and 69,488 KiB. These samples do not establish absence of leaks. Final clean-tree
counts and package qualification are recorded separately in `readiness.md`.

Semgrep is complementary and incomplete; see `readiness-semgrep.md` for every
finding, ignored test paths, rule parse errors and taint timeouts. Dependency
advisory scans are point-in-time. PyMuPDF uses an upstream native parser: the app
owns no C/C++/Rust parser implementation. Its Python process boundary is tested;
upstream native code was not fuzzed or sanitizer-qualified here. The small ctypes
no-overwrite wrapper was checked against the macOS SDK and actual race tests.
Linux's branch and other operating systems are unqualified.

No VoiceOver/Safari/Firefox qualification, lawyer-panel evaluation, real paid AI
success, OCR, adversarial same-user host isolation, power-loss filesystem guarantee,
or long-duration reliability proof is claimed. Preserve these limits in release
notes. The next broader analysis gate is independent, real contract annotation
with exception/scope disagreements reviewed by qualified people.
