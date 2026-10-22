# Clause Review Workbench handoff

Repository: https://github.com/Ethant35/clause-review-workbench
Local path: /Users/ethantarnarider/Documents/ChatGPT/Open source/clause-review-workbench
Release branch: main (implementation merged through PR #1). Final handoff update uses codex/release-handoff.
Application acceptance commit: 2c11357d4e2d9d4dffe9a2ce3a814301dfcb5523
Outcome: DONE for the core offline release, under the specification's explicit CR-18 exception. All applicable completion gates passed; release published and uploaded archive checksum verified.
Release: https://github.com/Ethant35/clause-review-workbench/releases/tag/v1.0.0
Tag: v1.0.0
Release commit: b9c359ab96ed92bfc9d496fc0f99998412e7c520
Release archive SHA-256: db86d3f044b25731940f6ca2961fa3daff1e6738d9fba1fd10b811a49f1a57a1
Remaining external gate: CR-18 successful real AI interpretation, explicitly UNVERIFIED. No other mandatory gate remains.

## Completed
- FastAPI/SQLite backend; React/TypeScript UI; DOCX/PDF/text source-preserving ingestion; 18-category commercial and six-category NDA playbooks.
- Deterministic review, exact anchors, missing-clause handling, uncertainty, liability properties, reviewer decisions/notes/history, YAML editing/import/export, Markdown/DOCX/JSON reports.
- Consent-gated OpenRouter adapter with model/provider selection, budgets, errors, and citation validation.
- CR-01 through CR-17, CR-19, CR-20 PASS. Additional security/retention E2E PASS. Twelve corpus scenarios pass, 11 planted deviations detected, 192 compliant controls pass, zero false positives/negatives/citation mismatches.
- Clean clone installation and fresh deployment archive browser workflow PASS. Visual DOCX/PDF and desktop/mobile review complete. Ethan author fields verified for generated DOCX/PDF.
- CR-18 BLOCKED_EXTERNAL: no authorized OpenRouter key/model/provider configuration. Core release is permitted, labeled AI-unverified.
- No GitHub Actions: repository setting enabled=false verified; no workflows created. Keep Actions disabled before any push, PR, tag, or release.

## Processes and usage
- No active Luna workers; both completed workers were interrupted/marked done.
- E2E and package smoke tests stop their servers in finally. Check artifacts/processes.json and, if necessary, run .venv/bin/python scripts/stop_processes.py.
- The session-local supported usage checker ran every 55 seconds in functions cell 11 during project work and is to be terminated at finalization. It uses get_usage_limits, writes artifacts/usage-check.json, and stops registered process groups on exhaustion. It is not a persistent automation and must be stopped when this project run ends.
- Latest checkpoint: 15% used, 85% remaining. Recheck live on resume. Stop all work at 100% used in an applicable window; do not use credits/resets/providers to bypass exhaustion.
- Local ignored artifacts include clean-install logs, synthetic reports, renders, package, screenshots, and test databases. Temporary clean checkouts and archive extraction directories are recorded under artifacts; they contain only synthetic data.

## Exact next-session commands
```sh
cd '/Users/ethantarnarider/Documents/ChatGPT/Open source/clause-review-workbench'
git status --short
git log -5 --oneline
gh api repos/Ethant35/clause-review-workbench/actions/permissions
gh pr list --state all
gh release view v1.0.0
cat artifacts/usage-check.json
cat artifacts/processes.json
```

The release exists and is public. The uploaded archive was downloaded again, compared byte-for-byte with the tested archive, and passed its published SHA256SUMS check. GitHub Actions remains disabled with zero workflow runs. PR #1 merged the implementation. Final handoff documentation is a separate docs-only PR and does not change release behavior.

For normal use run ./scripts/start.sh and open http://127.0.0.1:8765. No application server is intentionally left running. If resuming AI verification, supply authorized OPENROUTER_API_KEY, OPENROUTER_MODEL, and OPENROUTER_PROVIDER in the test environment and run .venv/bin/python tests/e2e.py. Do not claim production-verified AI until CR-18 passes. Existing tests and local logs remain under artifacts for inspection. No external analytics or GitHub Actions were used.

## Active quality reassessment
New objective ACTIVE (2026-10-22): adversarial verification of offline findings and source completeness. The prior v1.0.0 release remains published, but its 12-case corpus is not evidence of general semantic correctness. Current investigation: negated obligations/prohibitions and exceptions can satisfy regex conditions; empty XML element truthiness may bypass unsupported-content rejection. Write independent paired expectations, reproduce via real API, fix conservatively, preserve original controls, verify upgrade behavior and release only after local acceptance.
Branch: codex/evidence-boundary. No current application server. Usage checker functions cell 46 calls supported get_usage_limits every 55 seconds and writes artifacts/usage-check.json (latest 24% used). No Actions; enabled=false verified. Goal tool created a new bounded objective because no active goal was returned. Resume with git status, this handoff, and artifacts/adversarial-before.json once available.

### Reassessment checkpoint
Baseline committed as 32e0186: 31/81 adversarial checks passed; 50 failed. Conservative engine/parser fixes now pass 81/81 and preserve all original corpus cases. Real v1.0.0-to-current upgrade passed six checks: raw rows, notes, original bytes, all export warnings, browser re-upload, no outbound sockets. User expanded research to public GitHub and practitioner anecdotes. RESEARCH.md distinguishes official restricted Astra for Law access from public skills and anecdotes. New bounded change exposes existing saved playbook alternatives/fallback in UI and exports. E2E extension is in progress; one test reload selected the wrong document and is corrected. No public Astra access, credentials, or new integrations. Current changes remain uncommitted, next run all suites, inspect renders, commit, clean clone/package, then PR/release if green. Usage checker cell 46 remains active, latest 32% used; Actions remain disabled.

### Local acceptance complete, publication pending
Application commit 7a4a01073b366105992ad295b780eca84ddc3f46 passed a fresh clone installation, original E2E/corpus, 81/81 adversarial checks, and all six actual released-server upgrade checks. Packaged v1.0.1 deployment passed a fresh extraction/browser workflow. Final two-page report and historical warning inspected; saved DOCX author fields Ethan verified. Evidence is in evidence/quality; earlier root evidence remains historical. Source code is committed; final evidence/docs commit and PR/release follow. CR-18 remains BLOCKED_EXTERNAL; no public Astra for Law access was obtained. Usage 36% used at last checkpoint. Process registry empty after test cleanup. No Actions; enabled=false and zero runs verified.
