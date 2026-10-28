# Contract review verification map

Author: Ethan. Updated October 25, 2026.

| Journey | Source and executable proof | Observable end state |
| --- | --- | --- |
| Native launch and return | `native/Workbench.swift`, `native/bootstrap.py`; `tests/bundled_macos.py`, `tests/native_upgrade.py` | Fresh relocated bundle starts with system PATH and isolated data, serves the UI, restarts with the same data, then closes its port. Offline doctor/backup/restore preserve originals. |
| Intake and completeness | `backend/workbench/parsing.py`, `usability_intake.py`; `tests/test_usability_intake.py`, `tests/e2e.py`, `tests/usability_frontend.py` | Synthetic TXT, DOCX and text PDF retain valid source spans. Raster regions block analysis until the explicit visual comparison; scans remain unsupported. Reprocessing creates a new document. |
| Policy and analysis | `engine.py`, `relations.py`, `safety.py`, `frontend/src/App.tsx`; `tests/test_analysis_readiness.py`, `tests/test_sample_workflow.py`, `tests/review_context_e2e.py`, `tests/interactions_e2e.py`, `tests/adversarial_e2e.py` | Independent NDA expiry is located. Negation, conditions, survival and paragraph boundaries do not receive unsupported approval. Multiple exceptions remain visible. Reload restores the saved policy, while an explicit next-run policy change preserves the old result. |
| Source, decision and export | `frontend/src/App.tsx`, `backend/workbench/reports.py`; `tests/usability_frontend.py`, `tests/review_context_e2e.py`, `tests/e2e.py` | Highest priority is initially selected. Finding basis is separate from priority. Source jumps match exact evidence. Decisions/notes survive reload and appear in downloaded reports with policy provenance. |
| History and settings | `store.py`, `playbook_settings.py`, `safety.py`; `tests/test_playbook_settings.py`, `tests/test_usability_intake.py`, `tests/review_context_e2e.py`, `tests/native_upgrade.py` | A saved review retains its policy snapshot/results. Guidance edits do not change recognition patterns. New analysis/reprocessing preserves old notes and decisions without inheriting them into a new review. Old engine revisions are marked historical. |

The first sample is a synthetic commercial agreement with an explicit amendment
risk and interactions involving termination cost and indemnification limits. It
does not waive required rules to reduce the finding count. It is a workflow example,
not a recommended contract or legal-accuracy benchmark.

UX: show the policy behind saved results and the policy for a new run separately.
DX: reuse the app's harnesses and immutable review records. AX: retain accessible
control names, explicit API policy identifiers and source-linked exports.

Limits: one local user, macOS arm64 and Chromium. Automated assertions do not prove
unfamiliar-user usability, VoiceOver, OCR, successful live AI, general contract
interpretation, enforceability, or current release notarization. Local bundle
testing does not modify or requalify the published v1.3.0 assets.
