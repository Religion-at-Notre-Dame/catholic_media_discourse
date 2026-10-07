#!/usr/bin/env python3
"""Serve the interactive map locally and open a browser."""

from __future__ import annotations

import argparse
import http.server
import os
import socketserver
import subprocess
import threading
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE / "tools"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true")
    p.add_argument("--verify", action="store_true", help="run verify_site.py before serving")
    p.add_argument("--build-findings", action="store_true", help="rebuild findings-data.js first")
    args = p.parse_args()
    os.chdir(HERE)

    if args.build_findings:
        subprocess.check_call([sys_executable(), str(TOOLS / "build_findings_data.py")])
    if args.verify:
        subprocess.check_call([sys_executable(), str(TOOLS / "verify_site.py")])

    class Handler(http.server.SimpleHTTPRequestHandler):
        extensions_map = {
            **getattr(http.server.SimpleHTTPRequestHandler, "extensions_map", {}),
            ".js": "application/javascript",
            ".mjs": "application/javascript",
            ".json": "application/json",
            ".svg": "image/svg+xml",
            ".css": "text/css",
            ".wasm": "application/wasm",
        }

        def end_headers(self):
            # Story HTML: no cache. Heavy data blobs: short cache for local reloads.
            path = self.path.split("?", 1)[0]
            if path.endswith((".js", ".css", ".svg", ".png", ".json", ".csv")) and "index.html" not in path:
                self.send_header("Cache-Control", "public, max-age=60")
            else:
                self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def log_message(self, fmt, *a):
            print(fmt % a)

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", args.port), Handler) as httpd:
        url = f"http://127.0.0.1:{args.port}/pages/index.html"
        print(f"Classroom site → {url}")
        print("Layout: pages/  css/  js/  data/  branding/  tools/")
        print("Pages: pages/index.html  findings  methods  explore.html#/places|#/topics|#/santiago")
        if not args.no_browser:
            threading.Timer(0.4, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")


def sys_executable() -> str:
    import sys

    return sys.executable


if __name__ == "__main__":
    main()
