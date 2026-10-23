# Third-party notices

Author: Ethan. Inventory checked October 22, 2026 for version 1.3.0.

The repository's MIT license covers its original application code. Dependencies
retain their own licenses. It does not make the installed application or every
included component MIT-only. Upstream author and copyright notices are preserved.

The source archive includes application source, built frontend assets and notices.
The separate macOS app bundles Python, locked Python wheels and frontend assets.
Development Node tools and browsers are not bundled. The CPython runtime is the
hash-pinned Astral python-build-standalone 20260901 build. Its original Python and
component license texts and PYTHON.json accompany the app under Resources.

The native combined distribution is supplied subject to AGPLv3 terms. The
original application source retains its MIT grant; this does not remove the
AGPL obligations of the combined binary distribution. No commercial license is
supplied. The exact PyMuPDF and MuPDF corresponding source archives are available
as separate assets beside the app and workbench source on the same release.
[The source manifest](licenses/corresponding-source.json) records URLs, hashes and
rebuild instructions. Their upstream source and notices are unchanged.

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
