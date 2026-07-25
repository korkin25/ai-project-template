"""A minimal HTTP service (sample).

Exists only so the template's Dockerfile, Helm chart, and CI functional job have
something real to run. Replace with your service. Serves ``GET /health`` → 200 JSON.
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app import __version__


def health_payload() -> dict[str, str]:
    """The body returned by the health endpoint."""
    return {"status": "ok", "version": __version__}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path in ("/health", "/healthz", "/"):
            body = json.dumps(health_payload()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

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
    print(f"listening on http://{host}:{port}", flush=True)
    server.serve_forever()
