#!/usr/bin/env python3
"""
Launcher for the Scientific Evaluation Agent web GUI.

Usage
-----
    python gui.py                 # open http://127.0.0.1:5000
    python gui.py --port 8080
    python gui.py --host 0.0.0.0  # expose on the local network (see warning)

The app binds to 127.0.0.1 by default so it is reachable only from this
machine. It has no authentication: only use --host 0.0.0.0 on a network you
trust, since anyone who can reach the port could submit jobs and read reports.
"""

from __future__ import annotations

import argparse
import sys
import threading
import webbrowser


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run the evaluation agent GUI.")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Interface to bind (default: 127.0.0.1, this machine only).")
    parser.add_argument("--port", type=int, default=5000, help="Port (default: 5000).")
    parser.add_argument("--no-browser", action="store_true",
                        help="Do not open a browser window automatically.")
    parser.add_argument("--work-dir", default=None,
                        help="Where uploads and generated reports are stored "
                             "(default: a temp directory).")
    args = parser.parse_args(argv)

    try:
        from webapp import create_app
    except ImportError as exc:
        print(f"error: {exc}\nInstall the dependencies first:  pip install -r requirements.txt",
              file=sys.stderr)
        return 2

    app = create_app(work_root=args.work_dir)
    url = f"http://{'127.0.0.1' if args.host == '0.0.0.0' else args.host}:{args.port}"

    print(f"\n  Scientific Evaluation Agent — GUI")
    print(f"  Open: {url}")
    if args.host == "0.0.0.0":
        print("  WARNING: bound to all interfaces with no authentication.")
    print("  Press Ctrl+C to stop.\n")

    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    app.run(host=args.host, port=args.port, debug=False, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
