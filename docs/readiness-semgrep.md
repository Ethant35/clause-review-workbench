# Semgrep triage record

Author: Ethan

## Result

The final merged SARIF contains 52 results. I reviewed each result against the exact source line captured in the private local `artifacts/readiness/semgrep-final/triage.json`. The results are 49 informational long-line matches, two obfuscation-heuristic matches in floor-guard source text, and one tar-extraction traversal pattern in the package smoke script.

I found no confirmed exploitable security defect in the 30 findings that map to the intended release inventory. The tar rule is mitigated at the call site by `filter="data"` under the project’s Python `>=3.12` requirement. The other release-path results are readability or maintainability findings, not confirmed vulnerabilities. Several tracked frontend and playbook-generation lines are very long; the longest is 4,882 characters in the finding-detail JSX at `frontend/src/App.tsx:355`. That is real readability debt and remains open for a focused formatting change.

The 52-result total is not a count of 52 vulnerabilities. The final scan also read unexpected, untracked files with names ending in ` 2`; 22 findings point to those copies. Two additional heuristic results point to the new `scripts/floor-guard.mjs`, which is included in the release after staging. The packaging script builds its source list from `git ls-files`; the unexpected copies remain excluded. The scan path lists and triage rows preserve them as separate evidence; this review did not edit or remove them.

The initial merged scan had 27 results. The final scan had 52 because it used a broader, later working-tree snapshot that included the suffix-`2` copies and additional source lines. Line numbers and source files changed between snapshots, so the totals are not a like-for-like vulnerability delta.

## Scan coverage and limitations

Semgrep 1.182.1 ran in OSS mode without Pro. Nine scan commands completed; none were listed as failed or skipped. Two third-party scans were partial: Apiiro had three rule parse errors (one each in Dart, Java, and JavaScript/TypeScript patterns) and Elttam had 12 Java rule parse errors. The scanned third-party repositories are pinned by the SHAs in the local `triage.json`.

The final result count by selected ruleset was:

| Ruleset | Results | Files reported | Status |
| --- | ---: | ---: | --- |
| `p/secrets` | 0 | 133 | Complete command; 12 raw fixpoint timeouts |
| `p/security-audit` | 0 | 133 | Complete command; 13 raw fixpoint timeouts |
| Trail of Bits | 1 | 133 | Complete |
| Elttam | 0 | 133 | Partial; 12 Java rule parse errors |
| Apiiro | 51 | 37 | Partial; 3 language parser errors |
| `p/fastapi` | 0 | 26 | Complete |
| `p/python` | 0 | 26 | Complete command; 4 raw fixpoint timeouts |
| `p/react` | 0 | 6 | Complete |
| `p/typescript` | 0 | 6 | Complete |

The Python-specific file list includes the production modules `ai.py`, `diagnostics.py`, `engine.py`, `launcher.py`, `main.py`, `models.py`, `parser_worker.py`, `parsing.py`, `recovery.py`, `relations.py`, `reports.py`, `safety.py`, and `store.py`, plus the Python scripts recorded in the JSON. The TypeScript lists include `frontend/src/App.tsx`, `frontend/src/main.tsx`, and `frontend/vite.config.ts`. Exact paths for both language runs are included in the JSON; full `paths.scanned` lists remain in the raw scan outputs.

No `tests/` paths appear in any recorded scan list, consistent with Semgrep’s default test-file exclusion. Treat test code as outside this Semgrep coverage. The plan also did not include a dedicated JavaScript ruleset or a YAML ruleset. The TypeScript/React rules did run against six `.ts`/`.tsx` files. The Apiiro JavaScript/TypeScript parser error and lack of a dedicated JavaScript ruleset limit confidence for that language family. The 133-file cross-language inventories include 36 unexpected suffix-`2` paths. The output directory was excluded by `artifacts/readiness/semgrep-final`; no files were reported oversized.

The raw `fixpoint_timeouts` are analysis coverage warnings, not findings: 12 in `p/secrets`, 13 in `p/security-audit`, and four in `p/python`. They include current source files such as `ai.py`, `diagnostics.py`, `launcher.py`, `recovery.py`, and `relations.py`, as well as excluded duplicate copies. Zero reported findings in these scans do not clear the timed-out code paths. OSS mode also lacks Pro’s cross-file analysis.

## Manual disposition

- The 49 Apiiro `generic-one-liners` results match the rule’s `^.{400,}$` threshold. The source lines are structured model types, API request configuration, JSX, test/report records, or long playbook regular-expression calls. They do not show encoded payloads or concealed execution. They remain informational readability findings; the long JSX and rule-generation lines are valid maintainability debt.
- The two Apiiro `generic-obfuscation-operators` results are `scripts/floor-guard.mjs:79`, a regular expression that detects unfinished-work patterns, and line 80, an ordinary comment. The punctuation is rule-engine source text, not obfuscated behavior. The file was untracked during scanning and is included in the intended release. Its later exact status-selector replacement exception was manually reviewed and tested with positive and negative controls.
- Trail of Bits’ `tarfile-extractall-traversal` result is `scripts/deployment_smoke.py:18`. The script extracts a local package archive into a new temporary directory and explicitly passes Python’s `filter="data"`, which rejects unsafe archive paths and links. It is a local deployment-test helper, not the document-upload path. The path-traversal pattern is mitigated. This review did not separately test resource-exhaustion behavior for a hostile archive.

The final scan and source evidence are retained locally under `artifacts/readiness/semgrep-final/`, including raw JSON/SARIF, merged SARIF, scan status, and the exact 52-row manual triage. These detailed outputs and source excerpts are not published. The release contains this manual summary only. No scan was rerun for this triage task; no source, scanner configuration, or global setting was changed.

This review follows the explicitly invoked project-local Semgrep skill requirement to report partial scans, timeouts, and coverage gaps alongside findings.
