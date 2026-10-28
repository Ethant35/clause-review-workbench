# Mac app distribution

Author: Ethan.

The Apple Silicon app includes Python 3.12.14, the locked runtime dependencies,
and the built browser interface. It does not install software at first launch.
Download the DMG from the repository's release page, open it, drag **Clause Review
Workbench** to Applications, then open the app. The native launcher opens the
workbench at `http://127.0.0.1:8765`. Keep the launcher running while reviewing;
quit it to stop the local server.

Use **Use synthetic sample**, then **Run local review**. Select a finding and
**View in source**. **Confirm finding** records that you agree with the flagged
issue; **Dismiss finding** records that you do not. Neither choice approves or
changes contract terms. Save notes, then export. The document library and review
history are stored locally for your next visit.

The app remains a review aid for one trusted local user. It does not provide
hosted access, OCR, automatic extraction-completeness verification, or validated
general legal judgment. Image-bearing PDFs require a manual comparison of every
listed image region against the extracted text before analysis. Do not confirm
when an image contains terms missing from the text. Supply a complete text copy.

## Saved data and updates

The initial data folder is `~/Library/Application Support/Clause Review Workbench/Data`.
**Show saved data** reveals the current folder. No user data is stored in the app
bundle. Replacing the app does not replace the data. Quit the old app before
copying in an update. Back up first.

**Back up…** stops the server, verifies database integrity and original hashes,
and writes a new backup folder. **Restore backup…** checks a selected backup and
creates a separate data folder. It never overwrites an existing folder. The app
then uses the restored copy; the prior data remains available.

For a previous source/tar installation, stop that workbench and use **Import
earlier data…**. Choose its `.data` folder; Command-Shift-Period shows hidden
folders. The app creates and verifies a backup, then restores it to a separate
folder. The original installation remains unchanged. The old app must be stopped
because the offline recovery tools enforce the data lock.

Historical review results retain their decisions, notes and saved playbook.
**Reprocess original** creates a new document record using the current extractor.
It does not replace the original document or copy old decisions into new results.
Run a new review on the new record. Backups contain contract content; protect them
as you protect the originals.

## Remove the app

Quit the launcher, then move Clause Review Workbench from Applications to Trash.
This leaves saved contracts and reviews in the data folder. To remove those too,
use **Show saved data** before quitting, verify the folder, and remove it only after
saving any needed backup. If you used a restored or custom data location, that
folder is separate from the default Application Support folder. Exports, backups
and system backup copies remain until you remove them separately. Remove a saved
AI key using **Optional AI key…** before uninstalling if you no longer need it.

## Optional AI

Use **Optional AI key…** in the native launcher to store or remove an OpenRouter
key in this Mac's Keychain. Saving or removing restarts the local server. Local
review needs no key. Expand **Optional AI assistance** in a review to select an
exact provider/model, limits, and consent to that request. Keychain access failure
leaves AI unconfigured. No automatic provider fallback or retry is performed.
Successful live-provider quality is not qualified by local protocol tests.

## Troubleshooting

If startup fails, check for another service using port 8765, private data-folder
permissions, or an incomplete app copy. Restart after closing the other instance.
Use a backup if saved data is damaged. Never disable Gatekeeper to work around a
failed release signature. The built-in runtime also supports offline recovery:

```sh
APP='/Applications/Clause Review Workbench.app/Contents/Resources'
"$APP/python/bin/python3" -s -B "$APP/bootstrap.py" recover doctor \
  "$HOME/Library/Application Support/Clause Review Workbench/Data"
```

Only the tested macOS/Apple Silicon configuration is qualified. A deployment
target in the bundle is a loader minimum, not a claim that every older macOS
release was tested. Browser and native UI checks are automated developer checks,
not unfamiliar-user research.

## Build, sign and notarize

Build the frontend and run the acceptance suites first. `scripts/build_macos.py`
requires a new output path outside synced folders. Finder metadata inserted by a file provider can prevent signing; the tested build uses /private/tmp. It verifies upstream runtime archive hashes, installs
hash-locked wheels into the bundled runtime, preserves upstream licenses, compiles
the native launcher, and optionally signs every Mach-O before signing the app.
It does not read or change global Codex configuration or create Actions workflows.

```sh
.venv/bin/python scripts/build_macos.py --output '/private/tmp/crw-release/Clause Review Workbench.app' \
  --sign 'Developer ID Application: Ethan Tarnarider (Z2SL92S4B6)'
```

Notarize a ZIP of the signed app with `xcrun notarytool submit --keychain-profile
ethan-notary`. Check Apple's returned status. Staple the accepted app, create and
sign the DMG, notarize and staple that DMG, then verify `codesign`, `stapler`,
`spctl`, quarantine/download installation, and the published bytes. A build,
signature, or upload alone does not prove notarization. Final evidence records the
submission IDs and checksums; no credential is written to the repository.

## Source and licenses

The native distribution is supplied under the applicable AGPLv3 terms for its
PyMuPDF/MuPDF combination. Original workbench source retains its MIT grant;
upstream components retain their notices. No commercial Artifex license is
claimed. See [Third-party notices](../THIRD_PARTY_NOTICES.md) and
[corresponding source](../licenses/corresponding-source.json). Release downloads
include the workbench source and the exact PyMuPDF and MuPDF source archives.
