# Qualification constraints

Author: Ethan. Production qualification in progress; this file is not a readiness claim.

The supported target is one local user on the tested macOS arm64 host, Python 3.12,
Node 22 for builds, and Chromium. The server must bind to loopback. This is a
review aid for text contracts, not a substitute for source review or legal advice.
Hosted deployments, multiple users, OCR, and successful live AI analysis are not
qualified. The offline workflow must work without credentials or outbound traffic.

Release gates:

- Original source bytes, policy snapshots, decisions and historical rows survive upgrades.
- Exact evidence anchors round-trip. Unresolved scope and unsupported extraction are visible.
- Rollback cannot destroy an original. Interrupted cleanup is durable and retryable.
- Partial reviewer edits preserve untouched fields. Lists are bounded at 100 records.
- Parser concurrency, request size and analysis work have enforced limits.
- Recovery writes a new destination and validates the database and original hashes.
- Local diagnostics contain no contract text, filenames, IDs, credentials or raw URLs.
- Keyboard onboarding, skip/replay/return, actual sample review, error recovery and narrow layout pass.
- No known serious/critical accessibility violations in tested states; automated checks do not replace manual review.
- Existing E2E, adversarial, interaction and upgrade checks remain enabled; new regressions pass.
- Semgrep findings receive individual triage; partial coverage remains disclosed.
- GitHub Actions remain disabled with zero runs before publication operations.
- No global configuration, hooks, automatic source transmission or paid provider testing.

Tests may not be removed, skipped, weakened or replaced with implementation-shaped
expectations to obtain a green result. Any necessary expectation change needs an
independent reason and preserved before/after evidence. No arbitrary coverage quota.
