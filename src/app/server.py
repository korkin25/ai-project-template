"""A minimal HTTP service (sample).

Exists only so the template's Dockerfile, Helm chart, and CI functional job have
something real to run. Replace with your service.

It serves the two endpoints the service profile's runtime contract requires:
``GET /health`` → 200 JSON, and ``GET /metrics`` → 200 Prometheus text. The chart's
ServiceMonitor scrapes the second one, so the handler and the chart flag have to move
together: a ServiceMonitor pointing at a path the process does not serve is a scrape
target that fails silently — empty panels, and nobody told why.
"""

from __future__ import annotations

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app import __version__

# Prometheus text exposition format — the Content-Type a scraper expects. Serving JSON or
# `text/plain` without the version parameter makes the target scrape-able but unparseable.
CONTENT_TYPE_METRICS = "text/plain; version=0.0.4; charset=utf-8"

_STARTED_AT = time.monotonic()
_COUNTER_LOCK = threading.Lock()
_requests_total = 0


def app_version() -> str:
    """The released SemVer.

    ``APP_VERSION`` is set by the chart from ``.Chart.AppVersion``, which after packaging is
    the released version — the image cannot know its own tag. The packaged constant is only
    the fallback for a local run, so both endpoints report the same number either way.
    """
    return os.environ.get("APP_VERSION") or __version__


def health_payload() -> dict[str, str]:
    """The body returned by the health endpoint."""
    return {"status": "ok", "version": app_version()}


def metrics_payload() -> str:
    """Prometheus text exposition. A real service adds its own counters here.

    Hand-rolled rather than pulling a client library: a dependency here lands in the image,
    the SBOM and every CVE triage in exchange for a few lines of string formatting.

    Every label value is from a fixed, tiny set. A label with unbounded values — a request
    path, a user id, a raw error string — multiplies series until the metrics backend
    degrades; that belongs in a log field, not a metric label.
    """
    return (
        "# HELP app_build_info Build information; the value is always 1.\n"
        "# TYPE app_build_info gauge\n"
        f'app_build_info{{version="{app_version()}"}} 1\n'
        "# HELP app_uptime_seconds Seconds since this process started.\n"
        "# TYPE app_uptime_seconds gauge\n"
        f"app_uptime_seconds {time.monotonic() - _STARTED_AT:.3f}\n"
        "# HELP app_http_requests_total HTTP requests served by this process.\n"
        "# TYPE app_http_requests_total counter\n"
        f"app_http_requests_total {_requests_total}\n"
    )


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        global _requests_total
        # ThreadingHTTPServer serves each request on its own thread, so the counter needs a
        # lock: `+=` on an int is a read and a write, and a metric that quietly undercounts
        # is worse than no metric at all.
        with _COUNTER_LOCK:
            _requests_total += 1

        route = self.path.split("?", 1)[0]
        if route == "/metrics":
            self._respond(200, CONTENT_TYPE_METRICS, metrics_payload().encode())
        elif route in ("/health", "/healthz", "/"):
            self._respond(200, "application/json", json.dumps(health_payload()).encode())
        else:
            self._respond(404, "text/plain; charset=utf-8", b"not found\n")

    def _respond(self, status: int, content_type: str, body: bytes) -> None:
        """One write path for every route, so no response can forget Content-Length."""
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        """Silence the default per-request stderr logging."""


def make_server(host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    """Build (but do not start) the HTTP server. ``port=0`` picks a free port."""
    return ThreadingHTTPServer((host, port), Handler)


def run() -> None:
    """Console entry point (``app-serve``): serve until interrupted."""
    host = os.environ.get("APP_HOST", "0.0.0.0")
    port = int(os.environ.get("APP_PORT", "8080"))
    server = make_server(host, port)
    print(f"listening on http://{host}:{port} (/health, /metrics)", flush=True)
    server.serve_forever()
