#!/usr/bin/env python3
"""
Launcher for the Scientific Evaluation Agent web GUI.

Usage
-----
    python gui.py                 # open http://127.0.0.1:5000
    python gui.py --port 8080
    python gui.py --app-window    # open in a clean Edge/Chrome app window (demo)
    python gui.py --host 0.0.0.0  # expose on the local network (see warning)

Settings and API keys are read from ``.env`` in the project folder. Runs and
their reports are kept in ``./workspace`` so earlier evaluations can be
reopened after a restart.

The app binds to 127.0.0.1 by default so it is reachable only from this
machine. It has no authentication: only use --host 0.0.0.0 on a network you
trust, since anyone who can reach the port could submit jobs and read reports.
"""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def _load_env() -> None:
    """Load .env before anything reads os.environ (provider presets do)."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(PROJECT_ROOT / ".env")


def _free_port(host: str, preferred: int, attempts: int = 20) -> int:
    """Return ``preferred`` if it is free, else the next free port after it."""
    for port in range(preferred, preferred + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host if host != "0.0.0.0" else "127.0.0.1", port))
                return port
            except OSError:
                continue
    return preferred


def _open_ui(url: str, app_window: bool) -> None:
    if app_window:
        from scientific_evaluator.pdf_report import find_chromium

        browser = find_chromium()
        if browser:
            subprocess.Popen([browser, f"--app={url}", "--window-size=1440,900"])
            return
    webbrowser.open(url)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run the evaluation agent GUI.")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Interface to bind (default: 127.0.0.1, this machine only).")
    parser.add_argument("--port", type=int, default=5000,
                        help="Port (default: 5000; the next free one is used if busy).")
    parser.add_argument("--no-browser", action="store_true",
                        help="Do not open a browser window automatically.")
    parser.add_argument("--app-window", action="store_true",
                        help="Open in a chromeless Edge/Chrome window (good for demos).")
    parser.add_argument("--work-dir", default=str(PROJECT_ROOT / "workspace"),
                        help="Where uploads, reports and run history are stored "
                             "(default: ./workspace).")
    args = parser.parse_args(argv)

    _load_env()
    try:
        from webapp import create_app
    except ImportError as exc:
        print(f"error: {exc}\nInstall the dependencies first:  setup.bat  "
              "(or pip install -r requirements.txt)", file=sys.stderr)
        return 2

    app = create_app(work_root=args.work_dir)
    port = _free_port(args.host, args.port)
    url = f"http://{'127.0.0.1' if args.host == '0.0.0.0' else args.host}:{port}"

    print("\n  Scientific Evaluation Agent — GUI")
    print(f"  Open: {url}")
    if port != args.port:
        print(f"  (port {args.port} was busy, using {port})")
    if args.host == "0.0.0.0":
        print("  WARNING: bound to all interfaces with no authentication.")
    print("  Keep this window open during the demo. Press Ctrl+C to stop.\n")

    if not args.no_browser:
        threading.Timer(1.0, lambda: _open_ui(url, args.app_window)).start()

    try:
        from waitress import serve
    except ImportError:
        app.run(host=args.host, port=port, debug=False, threaded=True)
    else:
        serve(app, host=args.host, port=port, threads=8, _quiet=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
