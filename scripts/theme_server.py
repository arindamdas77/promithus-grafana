#!/usr/bin/env python3
"""Local theme studio for the monitoring dashboards.

Listens on 127.0.0.1:3013 unless THEME_STUDIO_BIND is set. Applying a theme
rewrites monitoring/theme/active.json and regenerates Grafana dashboard JSON.
It does not read Grafana passwords or change the monitoring containers.
"""

import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from theme_catalog import (  # noqa: E402
    ACTIVE_PATH,
    DEFAULT_ID,
    PRESETS,
    PREVIOUS_PATH,
    default_theme,
    load_theme,
    normalize_theme,
    validate_theme,
    write_json,
)

STUDIO = ROOT / "monitoring" / "theme-studio"
BUILD = [sys.executable, str(ROOT / "scripts" / "build_dashboards.py")]
MAX_BODY = 64_000


def _public_preset(preset):
    return {
        "id": preset["id"],
        "name": preset["name"],
        "grafanaTheme": preset["grafanaTheme"],
        "blurb": preset["blurb"],
        "colors": preset["colors"],
    }


def _read_previous():
    if not PREVIOUS_PATH.exists():
        return None
    try:
        return json.loads(PREVIOUS_PATH.read_text())
    except json.JSONDecodeError:
        return None


def _rebuild():
    return subprocess.run(BUILD, cwd=ROOT, capture_output=True, text=True, timeout=60, check=False)


def _store(theme):
    """Save a theme and rebuild dashboards. Roll back both files if the build fails."""
    errors = validate_theme(theme)
    if errors:
        return 400, {"ok": False, "errors": errors}
    theme = normalize_theme(theme)
    old_active = ACTIVE_PATH.read_text() if ACTIVE_PATH.exists() else None
    old_previous = PREVIOUS_PATH.read_text() if PREVIOUS_PATH.exists() else None
    if old_active is not None:
        PREVIOUS_PATH.write_text(old_active)
    write_json(ACTIVE_PATH, theme)
    result = _rebuild()
    if result.returncode != 0:
        if old_active is not None:
            ACTIVE_PATH.write_text(old_active)
        if old_previous is not None:
            PREVIOUS_PATH.write_text(old_previous)
        elif PREVIOUS_PATH.exists() and old_previous is None:
            PREVIOUS_PATH.unlink()
        _rebuild()
        detail = (result.stderr or result.stdout or "dashboard build failed").strip()
        return 500, {"ok": False, "errors": [detail]}
    return 200, {
        "ok": True,
        "theme": theme,
        "message": "Theme applied. Grafana reloads these files about every 10 seconds. Refresh the dashboards.",
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "ThemeStudio/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _authorized(self):
        expected = os.environ.get("THEME_STUDIO_TOKEN", "")
        if not expected:
            return True
        header = self.headers.get("Authorization", "")
        return header == f"Bearer {expected}"

    def _send(self, status, payload, content_type="application/json; charset=utf-8"):
        if isinstance(payload, (dict, list)):
            body = json.dumps(payload).encode()
        elif isinstance(payload, bytes):
            body = payload
        else:
            body = payload.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0 or length > MAX_BODY:
            return None, "Request body is empty or too large."
        try:
            return json.loads(self.rfile.read(length)), None
        except json.JSONDecodeError:
            return None, "Request body is not JSON."

    def do_GET(self):
        if not self._authorized():
            self._send(401, {"ok": False, "errors": ["This theme studio requires a bearer token."]})
            return
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send(200, {"ok": True})
            return
        if path == "/api/theme":
            self._send(200, {
                "active": load_theme(),
                "previous": _read_previous(),
                "presets": [_public_preset(item) for item in PRESETS],
                "limitations": [
                    "Grafana applies accent, series, gauge, and status colors from the generated dashboard JSON.",
                    "Page background, panel fill, panel border, table header, table row, and link chrome follow Grafana's light or dark preference. The preview shows the custom colors; dashboard JSON cannot set them.",
                    "Critical, warning, healthy, offline, and no-data hues are checked so a theme cannot hide a failure.",
                ],
            })
            return
        if path in {"/", "/index.html"}:
            page = STUDIO / "index.html"
            self._send(200, page.read_bytes(), "text/html; charset=utf-8")
            return
        self._send(404, {"ok": False, "errors": ["Not found."]})

    def do_POST(self):
        if not self._authorized():
            self._send(401, {"ok": False, "errors": ["This theme studio requires a bearer token."]})
            return
        path = urlparse(self.path).path
        if path == "/api/theme/apply":
            body, error = self._read_json()
            if error:
                self._send(400, {"ok": False, "errors": [error]})
                return
            status, payload = _store(body)
            self._send(status, payload)
            return
        if path == "/api/theme/reset":
            status, payload = _store(default_theme())
            self._send(status, payload)
            return
        if path == "/api/theme/restore":
            previous = _read_previous()
            if not previous:
                self._send(409, {"ok": False, "errors": ["There is no previous theme to restore."]})
                return
            status, payload = _store(previous)
            if status == 200:
                payload["message"] = "Previous theme restored. Refresh the Grafana dashboards."
            self._send(status, payload)
            return
        self._send(404, {"ok": False, "errors": ["Not found."]})


def main():
    bind = os.environ.get("THEME_STUDIO_BIND", "127.0.0.1")
    port = int(os.environ.get("THEME_STUDIO_PORT", "3013"))
    token = os.environ.get("THEME_STUDIO_TOKEN", "")
    if bind not in {"127.0.0.1", "::1", "localhost"} and not token:
        sys.stderr.write("Refusing to listen beyond localhost without THEME_STUDIO_TOKEN.\n")
        return 2
    if not ACTIVE_PATH.exists():
        write_json(ACTIVE_PATH, default_theme())
    if not PREVIOUS_PATH.exists():
        write_json(PREVIOUS_PATH, default_theme())
    if DEFAULT_ID not in {item["id"] for item in PRESETS}:
        sys.stderr.write("Default preset is missing.\n")
        return 2
    server = ThreadingHTTPServer((bind, port), Handler)
    print(f"theme studio http://{bind}:{port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
