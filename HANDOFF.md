# Clause Review Workbench handoff

Repository: https://github.com/Ethant35/clause-review-workbench
Local path: /Users/ethantarnarider/Documents/ChatGPT/Open source/clause-review-workbench
Branch: codex/build-workbench
Goal: ACTIVE. Build, verify locally, release v1.0.0 after acceptance.

## State
- Origin verified; starting repository had README and MIT license only.
- GitHub Actions disabled at repository level using actions/permissions; verified enabled=false. No workflows existed. Never enable or dispatch Actions.
- Startup account usage: 1% used, 99% remaining. Check periodically and stop at exhaustion.
- Architecture: Python 3.12 FastAPI, SQLite, React/TypeScript, offline rules, optional explicit OpenRouter consent.
- No acceptance checks have run. No release or PR exists yet.
- No running project servers yet.

## Next
Implement API, source parsing, rules, UI, independent synthetic corpus, live E2E tests, documentation. Use local acceptance only. CR-18 requires authorized available OpenRouter credentials; otherwise BLOCKED_EXTERNAL and release AI as unverified.

## Resume
```sh
cd '/Users/ethantarnarider/Documents/ChatGPT/Open source/clause-review-workbench'
git status --short
git log -3 --oneline
gh api repos/Ethant35/clause-review-workbench/actions/permissions
```

## Implementation milestone
Core parser, schema, rule engine, SQLite API, report exports and optional OpenRouter adapter implemented; integration checks pending. Frontend and independent corpus workers completed and were interrupted/marked done. No worker is running. Usage checker is actually running in this chat's functions cell 9, calling the supported tool every 55 seconds; this cell is session-local, not a persisted automation. Latest observed usage 5% used. Use artifacts/processes.json with scripts/stop_processes.py for project server cleanup once tests start.
