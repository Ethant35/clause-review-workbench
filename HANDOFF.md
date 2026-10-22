# Clause Review Workbench handoff

Author: Ethan. Updated October 22, 2026.
Repository: https://github.com/Ethant35/clause-review-workbench
Local path: /Users/ethantarnarider/Documents/ChatGPT/Open source/clause-review-workbench

## Current outcome

**DONE for the bounded offline corrective release v1.0.1.** Core acceptance passed under the specification's explicit CR-18 exception. Successful AI interpretation remains **BLOCKED_EXTERNAL / UNVERIFIED** because authorized OpenRouter key/model/provider configuration is absent.

Release: https://github.com/Ethant35/clause-review-workbench/releases/tag/v1.0.1
Release commit: bf115be7ba3e17ed7e5d6627edf47d7e033b2cab
Implementation/evidence PR: https://github.com/Ethant35/clause-review-workbench/pull/3 (merged).
Application acceptance commit: 7a4a01073b366105992ad295b780eca84ddc3f46
Packaged source commit: d51ac11 (later commits add evidence only).
Archive SHA-256: 76241f3aa8650acf5cf410b7277f9fce77230e175356436053143808991224af

The published archive was downloaded and matched byte-for-byte with the locally tested archive and SHA256SUMS. Every included tracked source file also matched packaged commit d51ac11. The release is public, not a draft or prerelease. Final handoff updates do not alter release behavior.

## Verified changes

- Fixed independently reproduced false assurance from negation, unresolved references, open-ended exceptions, unrelated notice periods, and mixed liability/indemnity scope. Positive controls remain intact.
- Reject unsupported DOCX content and PDFs with raster images, including logos. OCR remains unsupported. These gates are conservative and do not certify every possible extraction layout.
- Historical uploads/reviews retain original bytes, stored rows, decisions, and notes. Old results carry visible/exported warnings; fresh analysis requires downloading and re-uploading the original.
- UI/API/all exports expose acceptable alternatives and optional fallback wording from the saved playbook snapshot. Later policy edits cannot rewrite prior guidance; missing fallback is never invented.
- RESEARCH.md records Astra for Law's restricted access, public GitHub skills, named professional and self-reported user accounts, parser sources, and evidence limits. No Astra for Law access, private legal index, public API entitlement, new integration, plugin installation, or configuration change was obtained or implied.

## Acceptance

Fresh clone installation and production build passed. CR-01 through CR-17, CR-19, CR-20, and additional security/retention checks passed. CR-18 remains BLOCKED_EXTERNAL. The fixed adversarial suite improved from 31/81 to 81/81 with unchanged expectations. Original corpus: 12/12 scenarios, 11/11 planted deviations, 192 passing controls, no citation mismatch. Six real v1.0.0-to-current upgrade checks passed. Fresh archive extraction/browser upload/review/decision/export passed. npm audit: zero vulnerabilities. Final two-page report and browser warnings inspected. DOCX author and last-modified-by fields verified as Ethan; Finder/Windows shell displays were not separately verified.

Current evidence: evidence/quality and ACCEPTANCE.md. Earlier evidence files at evidence/ root are the historical v1.0.0 record. Synthetic expectations are not an independent lawyer panel, a held-out legal benchmark, or a general accuracy claim.

## Processes, usage, and continuation

No application server is intentionally left running; artifacts/processes.json is empty after cleanup. No active workers: the two original Luna workers completed and were interrupted. A session-local checker polled supported get_usage_limits every 55 seconds in functions cell 46 and is stopped at finalization; it is not a persistent automation. Latest checkpoint: 38% used, 62% remaining. Recheck live on resume. Stop at 100% used in an applicable window; do not use credits, resets, or other providers to bypass exhaustion.

**No GitHub Actions.** Repository enabled=false and zero runs were verified through publication. Recheck before any future push, PR, tag, or release. Do not add workflows. The Git working tree should be clean on main after the final docs PR.

Local ignored artifacts contain only synthetic test data, reports, screenshots, fresh-clone paths, and deployment logs. They are retained for review. No user contracts or credentials were committed. Do not change ~/.codex/config.toml without explicit authorization.

To run locally: ./scripts/start.sh, then http://127.0.0.1:8765. Keep loopback binding. For verification, run ./scripts/clean_acceptance.sh from a Git checkout containing tag v1.0.0. For optional real AI acceptance, supply authorized OPENROUTER_API_KEY, OPENROUTER_MODEL, and OPENROUTER_PROVIDER, then run .venv/bin/python tests/e2e.py. Do not claim verified AI before CR-18 passes.

The prior v1.0.0 release remains available for historical reproduction; PRs #1 and #2 created and documented that original release. Prefer v1.0.1 for current use.
