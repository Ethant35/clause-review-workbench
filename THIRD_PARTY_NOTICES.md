# Third-party notices

Author: Ethan. Inventory checked October 22, 2026 for version 1.2.0.

The repository's MIT license covers its original application code. Dependencies
retain their own licenses. It does not make the installed application or every
included component MIT-only. Upstream author and copyright notices are preserved.

The release archive includes application source, built frontend assets, and these
notices. It does not include the Python interpreter, Python wheels, node_modules,
or development browsers. Locked Python dependencies are installed separately by
`uv sync --frozen --python 3.12 --no-dev`. Node build/test tools are installed by
`npm ci` for source development and are not included in the release bundle.

## PyMuPDF and MuPDF

Installed PyMuPDF 1.28.2 declares dual licensing under GNU AGPL version 3 or an
Artifex commercial license. Its original [COPYING](licenses/python/pymupdf/COPYING)
is included. No commercial license is supplied or claimed. The [official licensing
documentation](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright)
confirms this choice. That current documentation covers a newer version; the
checked installed package metadata and COPYING establish the locked version's
license declaration.

Redistribution, modification, or network-service deployment must comply with the
applicable dependency terms. This local source release is not a commercial-license
grant or a legal certification for another deployment. The exact PyMuPDF source
archive and checksum are recorded in `uv.lock`; source URLs for all locked Python
runtime packages are in the inventory below. No upstream library source was
modified here. Hosted deployment is outside the tested support boundary.

## Inventory and preserved notices

[licenses/inventory.json](licenses/inventory.json) lists all 24 locked Python
runtime dependencies and the four frontend runtime packages bundled by Vite:
React, React DOM, Scheduler and Lucide React. Each entry records the installed
version, declared license, source location and copied notice paths. Python notices
are under `licenses/python/`; frontend notices are under `licenses/frontend/`.
The inventory's personal author is Ethan; upstream notices are exact copies.

The adapted local floor guard retains its separate
[MIT notice](licenses/floor-guard-MIT.txt). Dependency scans found no known
vulnerabilities in the installed Python environment or npm lockfile on the audit
date; that is a point-in-time advisory result, not a security or license guarantee.
