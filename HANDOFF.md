# Clause Review Workbench handoff

Repository: https://github.com/Ethant35/clause-review-workbench
Local path: /Users/ethantarnarider/Documents/ChatGPT/Open source/clause-review-workbench
Feature branch: codex/build-workbench
Application acceptance commit: 2c11357d4e2d9d4dffe9a2ce3a814301dfcb5523
Goal: Core implementation and all applicable local acceptance gates passed. Release publication is the remaining operational step at this checkpoint. Do not infer publication from this file; verify the release command below.

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
- The session-local supported usage checker runs every 55 seconds in functions cell 11. It uses get_usage_limits, writes artifacts/usage-check.json, and stops registered process groups on exhaustion. It is not a persistent automation and must be stopped when this project run ends.
- Latest checkpoint: 13% used, 87% remaining. Recheck live on resume. Stop all work at 100% used in an applicable window; do not use credits/resets/providers to bypass exhaustion.
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

If release exists, inspect its tag/commit and assets before doing new work. If not, commit only remaining acceptance/release documentation, push the feature branch with Actions disabled, create/attach a PR, merge after acceptance, tag v1.0.0, and publish the core offline release with the deployment archive and AI-unverified label. Build final archive using ./scripts/package.sh. Read ACCEPTANCE.md and evidence/*.json for exact outcomes. Run ./scripts/clean_acceptance.sh only after application changes; documentation-only release edits do not require repeating unchanged application tests.
