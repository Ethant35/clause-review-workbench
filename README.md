# clause-review-workbench
Open-source contract analysis and playbook review

Clause Review Workbench is a local browser application for commercial contract review. Upload a DOCX, text-based PDF, or UTF-8 text contract; compare it with editable YAML playbooks; inspect exact source passages; record reviewer decisions; and export Markdown, DOCX, or JSON reports.

**This is a contract-review aid, not legal advice or a substitute for attorney review.** Deterministic checks are narrow and return uncertainty where the configured conditions do not establish a result. Synthetic acceptance does not establish universal legal accuracy.

This v1.2.0 release is qualified only for the documented single-user local macOS workflow. The available tests do not establish broad contract-analysis accuracy, suitability for unsupervised legal decisions, or qualification of optional AI output.

Repository: [Ethant35/clause-review-workbench](https://github.com/Ethant35/clause-review-workbench). MIT licensed. Author: Ethan.

## Quick start

Prerequisites: Python 3.12+ (uv can install 3.12), [uv](https://docs.astral.sh/uv/), Node.js 22+, and npm. These commands work from the repository root:

```sh
git clone https://github.com/Ethant35/clause-review-workbench.git
cd clause-review-workbench
uv sync --frozen --python 3.12
npm --prefix frontend ci
npm --prefix frontend run build
.venv/bin/python -m uvicorn backend.workbench.main:app --host 127.0.0.1 --port 8765 --no-access-log
```

Open [the local workbench](http://127.0.0.1:8765). No API key is needed for offline review. Files remain in `.data` until deleted. Stop with Ctrl+C. Keep the service bound to loopback; it is for one trusted local user.

For the safe local launcher, first install the locked runtime dependencies and build the frontend, then run `./scripts/start.sh`:

```sh
uv sync --frozen --python 3.12 --no-dev
npm --prefix frontend ci
npm --prefix frontend run build
./scripts/start.sh
```

The start script does not install dependencies. It exits with setup instructions if `.venv/bin/python` is missing. The packaged archive does not include a Python environment; install the frozen dependencies explicitly after extracting it. See [startup guidance](docs/startup.md).

For separate development servers:

```sh
# Backend
.venv/bin/python -m uvicorn backend.workbench.main:app --host 127.0.0.1 --port 8765 --reload --no-access-log
# Frontend, in another terminal
npm --prefix frontend run dev
# Or install and launch both:
./scripts/dev.sh
```

Development UI: [localhost port 5173](http://127.0.0.1:5173), with `/api` proxied to the backend. Use the built production UI for confidential work.

## Review workflow

1. Upload a document and inspect extracted text and the original. PDF findings link to a page. DOCX/text findings use paragraph/block or line locations. Original bytes remain unchanged.
2. Select Commercial contracts or Mutual NDA, or create/import a playbook. Duplicate and edit YAML rules to fit the engagement. Run review.
3. Filter findings, inspect source text, and distinguish observed language from interpretation. Required missing provisions are explicitly marked as absence-based, with no quote.
4. Read “Related clauses and effect” when present. Inspect the cap, exception, definition, termination cost or qualified reference together. Each linked passage opens in source. A located reference is not a resolved legal conclusion.
5. Accept, reject, or leave issues unresolved; save reviewer notes. Open previous reviews after a restart. Rerunning creates a new review with a new policy snapshot.
6. Open “Saved playbook alternatives and fallback” for the selected finding. These positions come from the saved policy, not the contract or a verified legal standard. Later policy edits do not change earlier review guidance.
7. Export Markdown, DOCX, or JSON. Delete documents to remove sources and associated local review records.

The commercial playbook covers confidentiality, exclusions, permitted disclosures, term/expiration, automatic renewal, termination for convenience, termination for breach, liability cap, cap exceptions, indemnification, IP ownership, payment, unilateral amendment, data protection, subprocessors, audit rights, governing law, and assignment. The NDA playbook selects six relevant categories. Oregon governing-law preference is illustrative and configurable.

## Optional OpenRouter assistance

Optional AI assistance is not qualified for legal accuracy. Credentials are never required for offline review. Set `OPENROUTER_API_KEY` in the server environment, outside this repository, then restart. In the UI enter an exact model ID and OpenRouter provider name, set output-token and dollar budgets, and explicitly allow transmission. Consent resets after each request. No automatic provider/model fallback is allowed. If a request is interrupted after transmission may have started, the saved status is `OUTCOME_UNKNOWN`; the app does not retry automatically because a provider charge may already have occurred.

The server checks authentication and endpoint prices before sending extracted blocks and playbook guidance. It validates every returned quote; invalid citations reject the response. AI interpretations always need human review. See [PRIVACY.md](PRIVACY.md) and [ARCHITECTURE.md](ARCHITECTURE.md). Authentication and pricing behavior follows the [OpenRouter API reference](https://openrouter.ai/docs/api/reference/overview).

To run optional live acceptance against synthetic content, provide `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, and `OPENROUTER_PROVIDER` to the test process. This authorizes a bounded real request (test budget $0.10). Missing configuration is `BLOCKED_EXTERNAL`, never PASS. CR-19 always makes a real authentication request with a deliberately invalid credential and sends no contract.

## Local acceptance and packaging

```sh
.venv/bin/python -m playwright install chromium
.venv/bin/python tests/e2e.py
.venv/bin/python tests/adversarial_e2e.py
.venv/bin/python tests/interactions_e2e.py
.venv/bin/python tests/upgrade_e2e.py # Git checkout with the v1.0.0 tag
.venv/bin/python tests/upgrade_e2e.py --baseline v1.0.1
# Against an already running service; exports exact per-scenario scoring:
.venv/bin/python scripts/corpus_eval.py --output artifacts/corpus-results.json
# Clean local checkout install, build, and all E2E workflows:
./scripts/clean_acceptance.sh
# Reproducible local deployment package with built frontend:
./scripts/package.sh
```

Acceptance includes Python tests and real HTTP, Playwright Chromium, SQLite, DOCX/PDF parsing, and export checks. The v1.2.0 suite was reported as 87 pytest tests plus 2 unittest-style subtests; this count is a test inventory, not a legal-accuracy score. Results go to `artifacts/`; checked release evidence is in `evidence/` and [ACCEPTANCE.md](ACCEPTANCE.md). GitHub Actions are intentionally omitted and disabled at the repository level by owner instruction. Equivalent release checks run locally.

The deployment archive includes source, dependency lockfiles, built frontend, and `scripts/start.sh`, but no installed Python environment. After extracting it, run `uv sync --frozen --python 3.12 --no-dev`, then `./scripts/start.sh`. Dependency installation needs network access; subsequent offline reviews require no external network. Docker is not qualified by this release. The supported deployment evidence is limited to a single-user local macOS setup.

## Limits and configuration

- `CRW_DATA_DIR`: local storage path; default `.data`.
- `CRW_RETENTION_DAYS`: positive days to expire documents; `0` retains until deletion. Cleanup runs at startup and every minute.
- Uploads: 10 MiB; PDFs: 200 pages; extracted text: 300,000 characters/5,000 blocks. API lists use `limit`/`offset` pagination (maximum 100 rows); review history also offers a summary projection.
- OCR and encrypted PDFs are unsupported. PDFs containing any raster image (including logos) or a textless page are rejected. PDF annotations/comments/form fields are not extracted and produce a warning; side-by-side text layout and a capped layout check also produce warnings. DOCX revisions/macros/text boxes/notes/imports/content controls/fields/drawings and hidden text, including inherited default paragraph/character styles, are unsupported. DOCX headers/footers and comments are not analyzed and trigger warnings.
- Supported interactions are bounded and do not resolve every negation, cross-reference, definition, legal exception, or jurisdictional question. Exact Section/Clause labels are required for reference lookup. Match results require reading the complete agreement. Original PDF layouts can differ from extraction order.
- Downloads, filesystem backups, and SSD remnants are outside application deletion. No application-level encryption or multi-user access control is provided.

See [PLAYBOOK_SCHEMA.md](PLAYBOOK_SCHEMA.md), [SECURITY.md](SECURITY.md), [CONTRIBUTING.md](CONTRIBUTING.md), and the [local backup and recovery guide](docs/recovery.md).

## Upgrading from v1.0.0

Original files, decisions, and notes remain intact. Older uploads must be downloaded and uploaded again before a new review or AI request. Earlier reviews remain viewable and exportable with a historical/unverified warning; an upgrade does not rerun or certify them. New reviews use the current extraction and screening checks.

See [RESEARCH.md](RESEARCH.md) for the adversarial method, Astra for Law access research, public legal-workflow sources, and evidence limits. This app does not provide Astra for Law or its legal search index.

See [release and upgrade notes](RELEASE_NOTES.md), [qualification](docs/readiness.md), and [third-party license notices](THIRD_PARTY_NOTICES.md).

## Reporting a problem

Use the [repository issue tracker](https://github.com/Ethant35/clause-review-workbench/issues)
for ordinary bugs. Include the app version, OS/browser, a synthetic reproduction,
the step that failed, and its safe error/status code. Review local diagnostics
before sharing any excerpt. Do not attach real contracts, backups, credentials or
private exports. For a suspected vulnerability, follow [SECURITY.md](SECURITY.md)
instead of posting exploit details publicly.
