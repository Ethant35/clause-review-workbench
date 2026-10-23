# Local backup and recovery

Author: Ethan
Scope: single-user local macOS deployment with a local POSIX filesystem. The Linux implementation is present but has not been qualified.

The recovery command checks, copies, and restores the local SQLite database and its original source files. It does not upload files or call an external service. Stop the workbench before running it: the server holds an exclusive advisory lock for its full runtime.

Run these commands from the project root. Set `APP_DATA` to the exact directory configured by `CRW_DATA_DIR`; if that variable is unset, the application uses `.data` relative to its working directory. The backup or restore destination must be new, and its parent directory must already exist.

```sh
APP_DATA="/path/to/workbench-data"
PYTHONPATH=backend .venv/bin/python -m workbench.recovery doctor "$APP_DATA"
PYTHONPATH=backend .venv/bin/python -m workbench.recovery backup "$APP_DATA" "/path/to/backups/workbench-2026-10-22"
PYTHONPATH=backend .venv/bin/python -m workbench.recovery restore "/path/to/backups/workbench-2026-10-22" "/path/to/workbench-restored"
```

`doctor` runs SQLite integrity and foreign-key checks, validates saved JSON and original-source hashes, and reports a status and source count. It does not print document content or file hashes. A missing source directory fails without creating it. An unreferenced entry in `sources/` stops doctor and backup; recovery preserves it and never removes it automatically. Investigate that file before retrying. Backup and restore validate a schema-1 manifest containing SHA-256 hashes for the database and referenced original sources. Malformed JSON or manifest shapes produce stable, content-free errors. A hash mismatch, pending deletion, missing source, or active lock also stops the operation.

The implementation acquires a non-blocking `flock` on `.store.lock`. Restore verifies the manifest and copies under the same lock; the staged copy is hashed before publication. It stages a complete copy in a private temporary directory beside the destination, checks the staged database and source files, then uses the platform's atomic no-replace directory rename (`renamex_np(RENAME_EXCL)` on macOS or `renameat2(RENAME_NOREPLACE)` on Linux). An existing or concurrently created destination is preserved. Copy failures leave the final destination unpublished and do not alter database rows or original source files. A hard kill can leave a hidden `.crw-recovery-*` staging directory; after confirming no recovery command is running, inspect and remove only that staging directory. The `.store.lock` file may be created in a source or restored directory and is operational metadata.

Restore never overwrites a directory. Restore into a new path, run `doctor` on that path, then start the application against it using `CRW_DATA_DIR`. Keep the prior data directory until the restored instance has been checked. The tool does not switch application configuration, merge data, or roll back in place. If restore fails before publication, discard the chosen destination only if it was created by this operation; existing destinations are never adopted or replaced.

The trust boundary is the same operating-system user. `flock` coordinates the workbench and cooperating recovery commands; it does not defend against a hostile process running as that same user or one that modifies files while ignoring the lock. This is not a multi-user or network-filesystem backup service. Atomic no-overwrite publication is supported on macOS and Linux; other POSIX systems fail closed. Keep backups on access-controlled storage and validate them with `doctor` after restore. This workflow is not a substitute for independent, versioned backups.

The focused recovery checks run with:

```sh
PYTHONPATH=. .venv/bin/python -m pytest tests/test_recovery.py -q
```

They cover preserve-original behavior, malformed manifest and saved JSON, refusal to create a missing source, orphan-source refusal without deletion, interruption cleanup, a destination appearing at publish time, and lock retention through restore copy. The current run passed **15 tests**.
