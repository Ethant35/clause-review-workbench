"""Ethan: entry point for the self-contained app; no environment installation."""
import os
from pathlib import Path
import runpy
import sys
import signal
import threading

def watch_parent():
    """Exit if the native app that launched this child is gone."""
    raw_parent = os.environ.get('CRW_EXPECTED_PARENT_PID')
    try:
        expected_parent = int(raw_parent) if raw_parent is not None else os.getppid()
    except (TypeError, ValueError):
        raise SystemExit('Invalid parent process')
    if expected_parent < 1 or os.getppid() != expected_parent:
        raise SystemExit('Launching app is no longer running')

    def monitor():
        while True:
            threading.Event().wait(0.5)
            if os.getppid() != expected_parent:
                os.kill(os.getpid(), signal.SIGTERM)
                return

    threading.Thread(target=monitor, daemon=True).start()

command = sys.argv[1] if len(sys.argv) > 1 else ''
if command in {'serve', 'recover'}:
    # Validate the expected native parent before touching the working tree or
    # entering application code. This closes the launch/monitor startup race.
    watch_parent()
root = Path(__file__).resolve().parent / 'workbench'
sys.path.insert(0, str(root))
os.chdir(root)
if command == 'serve':
    from backend.workbench.launcher import main
    raise SystemExit(main())
if command == 'recover':
    sys.argv = ['workbench-recovery', *sys.argv[2:]]
    runpy.run_module('backend.workbench.recovery', run_name='__main__')
else:
    raise SystemExit('Unsupported app command')
