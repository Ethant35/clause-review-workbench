# Local startup

Author: Ethan

The supported deployment runs as one local user and listens only on loopback. Start it from the project root with:

```sh
./scripts/start.sh
```

Open `http://127.0.0.1:8765`. Stop the process with Ctrl+C. The launcher checks the saved Python environment, built frontend, configuration, data-directory permissions, and loopback port before it starts the app. It does not install or update packages during normal startup. This keeps a working deployment usable offline.

## First setup

For a source checkout, install the locked runtime dependencies and build the frontend once:

```sh
uv sync --frozen --python 3.12 --no-dev
npm --prefix frontend ci
npm --prefix frontend run build
./scripts/start.sh
```

Use Python 3.12 or newer and Node.js 22 with npm for setup. A deployment archive already includes its Python environment requirements and built frontend files, but needs a local `.venv` created at install time. The launcher does not run `uv`, `npm`, or a network request. If the project environment is missing or incomplete, it prints the setup command to run manually.

## Local settings

Set optional environment variables in the shell before launching:

| Setting | Default | Accepted values |
| --- | --- | --- |
| `CRW_PORT` | `8765` | Integer from 1 through 65535. The service still binds to `127.0.0.1`. |
| `CRW_DATA_DIR` | `.data` | Nonempty local directory. Relative paths resolve from the project root. The directory must have mode `700`; the launcher creates a missing directory with that mode and never changes an existing directory's permissions. |
| `CRW_RETENTION_DAYS` | `0` | `0` disables expiration; `1` through `36500` expires older documents. |

For example:

```sh
CRW_PORT=8877 CRW_DATA_DIR="$HOME/contract-workbench" CRW_RETENTION_DAYS=90 ./scripts/start.sh
```

The app stores originals and reviews locally. Retention can delete expired records and originals. Read [the privacy notes](../PRIVACY.md) before setting a positive retention period.

## Startup errors

The launcher gives short diagnostics and avoids printing exception traces, local paths, or saved content.

| Message | What to do |
| --- | --- |
| Project Python environment is missing or incomplete | Install `uv`, then run `uv sync --frozen --python 3.12 --no-dev` from the project root. |
| Built frontend is missing or incomplete | Run `npm --prefix frontend ci` and `npm --prefix frontend run build` from the project root. |
| `CRW_PORT` is invalid or already in use | Choose a number from 1–65535. If another local service owns the port, stop it or set a different `CRW_PORT`. |
| `CRW_DATA_DIR` must have private permissions | Stop the workbench. Inspect the configured directory, then set its permissions to `700` yourself. Startup does not relax existing permissions. |
| Data directory is already in use | Stop the other workbench process using that directory, then start again. Do not run two instances against one data directory. |
| Saved local data could not be opened | Stop the workbench. Run the offline `doctor` command below and follow [the recovery guide](recovery.md). The launcher does not repair or replace the database. |

To check storage while the app is stopped, run this from the project root. Set `CRW_DATA_DIR` to the directory used by the app; if unset, the default is `.data`:

```sh
APP_DATA="${CRW_DATA_DIR:-.data}"
PYTHONPATH=backend .venv/bin/python -m workbench.recovery doctor "$APP_DATA"
```

The doctor reports an integrity status and source count, not contract content. A failed check does not change or repair the data. Preserve the original directory and follow the recovery guide before attempting a restore.
