"""Group-(a) tests for the sample app. Replace with your real tests."""

from __future__ import annotations

import json
import threading
import urllib.request

from app import __version__
from app.server import health_payload, make_server


def test_version_is_semver() -> None:
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_health_payload() -> None:
    payload = health_payload()
    assert payload["status"] == "ok"
    assert payload["version"] == __version__


def test_server_serves_health() -> None:
    server = make_server("127.0.0.1", 0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as resp:
            assert resp.status == 200
            data = json.loads(resp.read())
            assert data["status"] == "ok"
    finally:
        server.shutdown()
