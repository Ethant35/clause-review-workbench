---
name: verify-clause-review-workbench
description: Verify this repository's local contract review workflow using its existing source, browser and native harnesses. Invoke explicitly by this file path; this is not a publication procedure.
---

Author: Ethan.

Run from the repository root. This folder is local to this app; do not move it into
the shared `.agents/skills` symlink. No picker discovery or global installation is
claimed. Read [feature-map.md](feature-map.md) before selecting checks.

## Prepare and doctor

1. Record `git rev-parse HEAD`, `git diff --stat`, the current usage reading and
   relevant environment limits. Preserve unrelated files. Honor the active usage
   guard and stop its poller when waiting or done. Never use GitHub Actions or AI
   provider calls for this procedure.
2. Check `.venv/bin/python`, `frontend/node_modules` and the pinned lockfiles.
   If dependencies are absent, restore the project's locked environment only:
   `uv sync --frozen --python 3.12` and `npm ci --prefix frontend`. Do not upgrade
   locks, install browser binaries or add global tools without task authorization.
3. Create a new `artifacts/verification-<unique-id>` evidence directory. Record all
   exit codes and log paths there. Run `npm run build --prefix frontend`.
4. Each browser harness starts `tests/serve_checked.py` on a fresh loopback port,
   in a separate scratch data directory, removes the provider key, and waits for
   `/api/health`. The health response must report the current extraction/review
   revisions. A passing HTTP health check alone is not a passing UI journey.

## Execute

Run these existing harnesses sequentially and retain stdout/stderr. A nonzero
exit or failed assertion is a finding; do not alter the map to conceal it.

```sh
.venv/bin/python -m pytest -q --ignore-glob='* 2.py'
.venv/bin/python tests/e2e.py
.venv/bin/python tests/interactions_e2e.py
.venv/bin/python tests/adversarial_e2e.py
.venv/bin/python tests/usability_frontend.py
.venv/bin/python tests/review_context_e2e.py
```

The ignore glob excludes unrelated preserved duplicate files, not canonical
tests. Unset `CRW_ALLOW_PROVIDER_REJECTION_TEST` and `CRW_ALLOW_LIVE_AI_TEST` before
this run. Inspect the E2E result JSON: both provider cases (including invalid-key
rejection) stay blocked without separate authorization. Report them as blocked,
not passed. Browser tests
must stay headless and all document inputs synthetic. Inspect the saved screenshot
from the focused review-context test as well as its assertions.

For a native/source change, build a NEW local test bundle; never alter a published
or installed app. Use the existing build script and runtime cache:

```sh
.venv/bin/python scripts/build_macos.py --output /private/tmp/crw-verification-<unique-id>/Clause\ Review\ Workbench.app
.venv/bin/python tests/bundled_macos.py /private/tmp/crw-verification-<unique-id>/Clause\ Review\ Workbench.app --report artifacts/verification-<unique-id>/native.json
.venv/bin/python tests/native_upgrade.py /private/tmp/crw-verification-<unique-id>/Clause\ Review\ Workbench.app --baseline v1.3.0
```

Replace `<unique-id>` consistently with the chosen directory. Stage intended new source/docs/license files before a Git-checkout build; the
builder uses the index to exclude unrelated untracked copies. Build outside synced
folders. Match the bundle's
`Contents/Resources/build-manifest.json` source hashes against the current checkout
and compare bundled `frontend/dist` files. These tests launch with isolated app
support/data and a system-only PATH. This unsigned local bundle is test evidence,
not a distributable release or Gatekeeper acceptance. If the cache, native compiler
or Chromium is unavailable, report that path blocked; do not substitute an older
binary and claim it tests changed sources.

## Inspect and finish

Check the map's observable end states, source anchor assertions, network audit
files, and saved review/export snapshots. New recognition must not silently turn
conditions, negation, survival-only language or unresolved references into approval.
Keep old review records, policy snapshots, notes and decisions intact.

Harnesses terminate their owned servers in `finally` and retain evidence. Verify
their processes exited and ports closed; clean up only processes owned by this run.
Close any manually opened hidden test tab. Keep logs, screenshots and test data
under `artifacts`; do not publish raw evidence or user data. Report current passes,
failures, blocked paths and evidence paths separately from earlier release results.
No notarization, upload, release or general legal-accuracy claim follows from this
skill's success. Update the map when a user journey changes, preserving regressions.
