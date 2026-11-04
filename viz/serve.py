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
ROOT = HERE.parent
TOOLS = HERE / "tools"
BASEMAP_KEY_JS = HERE / "js" / "basemap-key.js"


def _env_value(name: str) -> str:
    """Read one variable from the repo .env, then the process environment."""
    env_path = ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key.strip() != name:
                continue
            value = value.strip().strip('"').strip("'")
            return value
    return os.environ.get(name, "").strip()


def write_basemap_key_js() -> None:
    """Expose CARTO_BASEMAP_KEY to the static map without committing the key."""
    key = _env_value("CARTO_BASEMAP_KEY")
    escaped = key.replace("\\", "\\\\").replace('"', '\\"')
    BASEMAP_KEY_JS.write_text(
        f'window.CARTO_BASEMAP_KEY = "{escaped}";\n',
        encoding="utf-8",
    )
    if key:
        print("CARTO basemap key loaded from .env")
    else:
        print("CARTO_BASEMAP_KEY is empty — set it in .env and restart")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true")
    p.add_argument("--verify", action="store_true", help="run verify_site.py before serving")
    p.add_argument(
        "--build-findings",
        action="store_true",
        help="rebuild findings-data.js and triage-data.js first",
    )
    args = p.parse_args()
    os.chdir(HERE)
    write_basemap_key_js()

    if args.build_findings:
        subprocess.check_call([sys_executable(), str(TOOLS / "build_findings_data.py")])
        subprocess.check_call([sys_executable(), str(TOOLS / "build_triage_data.py")])
        subprocess.check_call([sys_executable(), str(TOOLS / "build_figures_data.py")])
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
            path = self.path.split("?", 1)[0]
            # Classroom snapshots + renderers: never cache (Story/Findings/Triage).
            no_store = (
                "findings-data.js" in path
                or "triage-data.js" in path
                or "figures-data.js" in path
                or path.endswith("/story.js")
                or path.endswith("/findings.js")
                or path.endswith("/triage.js")
                or path.endswith("/figures.js")
                or path.endswith("/site.js")
                or path.endswith(".html")
                or "index.html" in path
            )
            if no_store:
                self.send_header("Cache-Control", "no-store")
            elif path.endswith((".js", ".css", ".svg", ".png", ".json", ".csv")):
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
        print(
            "Pages: pages/index.html  findings  triage  methods  "
            "explore.html#/places|#/topics|#/santiago"
        )
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
