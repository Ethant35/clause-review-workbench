# Contributing

Author: Ethan

Use Python 3.12+, Node 22+, uv, and the documented development commands. Keep changes on a feature branch. Preserve MIT licensing and source evidence. Do not add analytics or network dependencies to offline review.

All automated tests are end-to-end: launch the actual API/browser, database, parsers and exports. Do not add unit tests or fake model responses. New legal screening behavior needs independently written positive/negative synthetic fixtures and stable rule IDs before scoring application output. Do not weaken manifests to match observed results. Document ambiguity honestly.

Run `uv sync --frozen --python 3.12`, `npm --prefix frontend ci`, `npm --prefix frontend run build`, and `.venv/bin/python tests/e2e.py`. Run `scripts/clean_acceptance.sh` before release. Inspect export rendering and browser screenshots. Do not commit contracts, keys, local databases, downloaded reports, or logs. Use synthetic examples only. Personal author metadata on repository-generated documents is Ethan; factual application metadata remains truthful.

No GitHub Actions: do not create workflows or dispatch them. Check `gh api repos/Ethant35/clause-review-workbench/actions/permissions` before pushes/tags and ensure `enabled` is false. Submit a pull request with local checks, limitations, and any externally blocked provider validation.
