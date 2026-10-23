"""Safe diagnostics for the supported single-user local launcher."""

from contextlib import asynccontextmanager
from dataclasses import dataclass
import errno
import importlib.util
import json
import logging
import os
from pathlib import Path
import re
import socket
import sqlite3
import sys
import threading


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_MODULES = (
    "fastapi",
    "uvicorn",
    "multipart",
    "docx",
    "fitz",
    "pydantic",
    "yaml",
    "httpx",
    "regex",
    "defusedxml",
)


class LauncherError(Exception):
    """Expected setup or configuration failure with content-free guidance."""


class StartupFailure(Exception):
    """Sanitized lifespan failure used to avoid Uvicorn tracebacks."""


@dataclass(frozen=True)
class Settings:
    port: int
    data_dir: str
    retention_days: int


def parse_settings(environ=None):
    environ = os.environ if environ is None else environ
    port_text = environ.get("CRW_PORT", "8765")
    if not re.fullmatch(r"[0-9]{1,5}", port_text):
        raise LauncherError("CRW_PORT must be a number from 1 through 65535.")
    port = int(port_text)
    if not 1 <= port <= 65535:
        raise LauncherError("CRW_PORT must be a number from 1 through 65535.")

    data_dir = environ.get("CRW_DATA_DIR", ".data")
    if not data_dir.strip():
        raise LauncherError("CRW_DATA_DIR must name a nonempty local directory.")

    retention_text = environ.get("CRW_RETENTION_DAYS", "0")
    if not re.fullmatch(r"[0-9]{1,5}", retention_text):
        raise LauncherError("CRW_RETENTION_DAYS must be 0 or a number from 1 through 36500.")
    retention_days = int(retention_text)
    if not 0 <= retention_days <= 36500:
        raise LauncherError("CRW_RETENTION_DAYS must be 0 or a number from 1 through 36500.")

    return Settings(port=port, data_dir=data_dir, retention_days=retention_days)


def check_frontend_build(project_root=PROJECT_ROOT):
    """Reject a missing or partially copied built frontend before server startup."""
    dist = Path(project_root) / "frontend" / "dist"
    index = dist / "index.html"
    if dist.is_symlink() or index.is_symlink() or not index.is_file():
        raise LauncherError(
            "Built frontend is missing or incomplete. Run `npm --prefix frontend ci && npm --prefix frontend run build` from the project directory."
        )
    try:
        markup = index.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise LauncherError(
            "Built frontend is missing or incomplete. Run `npm --prefix frontend ci && npm --prefix frontend run build` from the project directory."
        ) from None
    asset_paths = re.findall(r"(?:src|href)=[\"'](/?assets/[^\"']+)[\"']", markup)
    if not asset_paths:
        raise LauncherError(
            "Built frontend is missing or incomplete. Run `npm --prefix frontend ci && npm --prefix frontend run build` from the project directory."
        )
    for asset in asset_paths:
        relative = asset.lstrip("/")
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise LauncherError("Built frontend is missing or incomplete. Rebuild it from the project directory.")
        candidate = dist
        unsafe = False
        for part in relative_path.parts:
            candidate = candidate / part
            unsafe = unsafe or candidate.is_symlink()
        if unsafe or not candidate.is_file():
            raise LauncherError(
                "Built frontend is missing or incomplete. Run `npm --prefix frontend ci && npm --prefix frontend run build` from the project directory."
            )


def missing_modules():
    missing = []
    for module in REQUIRED_MODULES:
        try:
            if importlib.util.find_spec(module) is None:
                missing.append(module)
        except (ImportError, ValueError):
            missing.append(module)
    return missing


def prepare_data_directory(data_setting):
    """Create the private configured leaf; never relax permissions on existing data."""
    candidate = Path(data_setting)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    if candidate.is_symlink():
        raise LauncherError("CRW_DATA_DIR must not be a symbolic link.")
    try:
        candidate.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not candidate.is_dir():
            raise LauncherError("CRW_DATA_DIR must name a directory.")
        if candidate.stat().st_mode & 0o077:
            raise LauncherError(
                "CRW_DATA_DIR must have private permissions (chmod 700). The launcher does not change existing permissions."
            )
    except LauncherError:
        raise
    except OSError:
        raise LauncherError("CRW_DATA_DIR could not be created or accessed. Check its permissions and available disk space.") from None


def startup_diagnostic(exc):
    if isinstance(exc, RuntimeError) and "data directory is in use" in str(exc).lower():
        return "Data directory is already in use. Stop the running workbench before starting another."
    if isinstance(exc, sqlite3.Error):
        return (
            "Saved local data could not be opened. Stop the workbench, then run the offline doctor command; "
            "see docs/recovery.md for the safe recovery steps."
        )
    if isinstance(exc, (ValueError, PermissionError)) and "private" in str(exc).lower():
        return "CRW_DATA_DIR must have private permissions (chmod 700). The launcher does not change existing permissions."
    if isinstance(exc, (OSError, PermissionError)):
        return "The local data directory could not be accessed. Check its permissions and available disk space."
    return "Startup failed. See docs/startup.md for diagnosis; private paths and saved content were not printed."


class _SafeUvicornErrors(logging.Filter):
    """Remove exception details from Uvicorn's startup failure record."""

    def filter(self, record):
        try:
            unsafe_message = "Traceback (most recent call last)" in record.getMessage()
        except Exception:
            unsafe_message = True
        if record.exc_info or unsafe_message:
            record.msg = "Application startup failed; see the safe guidance printed by the workbench."
            record.args = ()
            record.exc_info = None
            record.exc_text = None
        return True


class _SafeLifespanMessages:
    """Strip Starlette's formatted startup traceback before Uvicorn can log it."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "lifespan":
            return await self.app(scope, receive, send)

        async def safe_send(message):
            if message.get("type") in {"lifespan.startup.failed", "lifespan.shutdown.failed"} and message.get("message"):
                message = {**message, "message": "Application lifecycle failed; private details were not printed."}
            await send(message)

        await self.app(scope, receive, safe_send)


def _guard_lifespan(app):
    original = app.router.lifespan_context

    @asynccontextmanager
    async def safe_lifespan(application):
        context = original(application)
        try:
            await context.__aenter__()
        except Exception as exc:
            print(startup_diagnostic(exc), file=sys.stderr, flush=True)
            raise StartupFailure("Local application startup failed") from None
        try:
            yield
        except BaseException as exc:
            suppress = await context.__aexit__(type(exc), exc, exc.__traceback__)
            if not suppress:
                raise
        else:
            await context.__aexit__(None, None, None)

    app.router.lifespan_context = safe_lifespan
    return _SafeLifespanMessages(app)


def main():
    os.chdir(PROJECT_ROOT)
    if sys.version_info < (3, 12):
        print("Python 3.12 or newer is required. Recreate the project environment with the documented setup command.", file=sys.stderr)
        return 2
    try:
        settings = parse_settings()
        check_frontend_build()
    except LauncherError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    absent = missing_modules()
    if absent:
        print(
            "The project Python environment is incomplete. Run `uv sync --frozen --python 3.12 --no-dev` from the project directory.",
            file=sys.stderr,
        )
        return 2
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Permit a prompt restart after our closed connections enter TIME_WAIT.
    # SO_REUSEPORT is deliberately absent: a live listener still owns the port.
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        listener.bind(("127.0.0.1", settings.port))
        listener.listen(socket.SOMAXCONN)
    except OSError as exc:
        listener.close()
        if exc.errno == errno.EADDRINUSE:
            print("CRW_PORT is already in use. Stop the other local service or choose another port.", file=sys.stderr)
        else:
            print("The workbench could not bind its loopback port. Check local port permissions and CRW_PORT.", file=sys.stderr)
        return 2
    try:
        prepare_data_directory(settings.data_dir)
    except LauncherError as exc:
        listener.close()
        print(str(exc), file=sys.stderr)
        return 2

    try:
        from .main import app
        import uvicorn
    except (ImportError, ModuleNotFoundError):
        listener.close()
        print(
            "The project Python environment is incomplete. Run `uv sync --frozen --python 3.12 --no-dev` from the project directory.",
            file=sys.stderr,
        )
        return 2
    except Exception:
        listener.close()
        print("The local application could not be loaded. Check the Python environment and docs/startup.md.", file=sys.stderr)
        return 2

    safe_app = _guard_lifespan(app)
    safe_filter = _SafeUvicornErrors()
    filtered_handlers = []
    try:
        config = uvicorn.Config(safe_app, host="127.0.0.1", port=settings.port, access_log=False, timeout_graceful_shutdown=10)
        server = uvicorn.Server(config)
        ready_stop = threading.Event()
        def announce_ready():
            # Private per-launch IPC. Never infer readiness from another service
            # that happens to answer on the requested port.
            target = os.environ.get("CRW_READY_FILE")
            if not target:
                return
            while not ready_stop.wait(0.05):
                if server.started:
                    try:
                        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                        with os.fdopen(descriptor, "w") as output:
                            json.dump({"url": f"http://127.0.0.1:{listener.getsockname()[1]}"}, output)
                    except OSError:
                        server.should_exit = True
                    return
        ready_thread = threading.Thread(target=announce_ready, daemon=True)
        ready_thread.start()
        # Config applies Uvicorn's logging configuration, so attach the filter after it.
        for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.lifespan"):
            logging.getLogger(logger_name).addFilter(safe_filter)
            for handler in logging.getLogger(logger_name).handlers:
                handler.addFilter(safe_filter)
                filtered_handlers.append(handler)
        with listener:
            server.run(sockets=[listener])
        ready_stop.set()
        ready_thread.join(timeout=1)
        return 0 if server.started else 1
    except SystemExit:
        return 1
    except Exception:
        print("Startup failed. See docs/startup.md for diagnosis; private paths and saved content were not printed.", file=sys.stderr)
        return 1
    finally:
        for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.lifespan"):
            logging.getLogger(logger_name).removeFilter(safe_filter)
        for handler in filtered_handlers:
            handler.removeFilter(safe_filter)


if __name__ == "__main__":
    raise SystemExit(main())
