"""Group-(a) tests for the sample app. Replace with your real tests.

The `/metrics` tests are not decoration. The service profile makes the endpoint part of the
runtime contract, and the chart's ServiceMonitor scrapes it — so a regression here does not
produce a red test in the consuming repo, it produces a scrape target that 404s, empty
panels, and no alert (the alert needs the series that never arrived). These are the only
things standing between that and a release.
"""

from __future__ import annotations

import contextlib
import json
import re
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator

import pytest

from app import __version__
from app.server import (
    CONTENT_TYPE_METRICS,
    app_version,
    health_payload,
    make_server,
    metrics_payload,
)


@contextlib.contextmanager
def serving() -> Iterator[str]:
    """Run the real server on an ephemeral port and yield its base URL.

    Exercised over HTTP rather than by calling the payload functions directly, because the
    header the scraper depends on is set by the handler, not by the payload — a test that
    only calls ``metrics_payload()`` passes while the endpoint answers with the wrong
    Content-Type, which is exactly the failure that shows up as a green target and no data.
    """
    server = make_server("127.0.0.1", 0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()


def build_info_version(exposition: str) -> str:
    """Pull the `version` label out of `app_build_info` — the sample's one labelled series."""
    match = re.search(r'^app_build_info\{version="([^"]+)"\} 1$', exposition, re.MULTILINE)
    assert match, f"no app_build_info series in:\n{exposition}"
    return match.group(1)


def test_version_is_semver() -> None:
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_health_payload() -> None:
    payload = health_payload()
    assert payload["status"] == "ok"
    assert payload["version"] == __version__


def test_app_version_falls_back_to_the_packaged_constant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No APP_VERSION: report the packaged number, which is what a local run has."""
    monkeypatch.delenv("APP_VERSION", raising=False)

    assert app_version() == __version__


def test_app_version_prefers_the_chart_injected_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """APP_VERSION wins.

    This is how the chart passes `.Chart.AppVersion` in — the released SemVer, which the
    image cannot know about itself. Without this precedence every pod in the fleet reports
    the packaged placeholder and no operator can map a running pod back to a commit.
    """
    monkeypatch.setenv("APP_VERSION", "4.5.6")

    assert app_version() == "4.5.6"


def test_app_version_ignores_an_empty_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty string is an unset variable, not a version.

    A ConfigMap key with no value renders as `APP_VERSION=""`, and reporting an empty version
    would be a valid-looking response carrying nothing.
    """
    monkeypatch.setenv("APP_VERSION", "")

    assert app_version() == __version__


def test_server_serves_health() -> None:
    with serving() as base, urllib.request.urlopen(f"{base}/health", timeout=5) as resp:
        assert resp.status == 200
        data = json.loads(resp.read())
        assert data["status"] == "ok"


def test_server_serves_metrics_as_prometheus_text() -> None:
    """200 with the exposition Content-Type, header parameter included.

    Serving `text/plain` without `version=0.0.4` makes the target scrape-able and the sample
    unparseable: Prometheus marks the target up and stores nothing.
    """
    with serving() as base, urllib.request.urlopen(f"{base}/metrics", timeout=5) as resp:
        assert resp.status == 200
        assert resp.headers["Content-Type"] == CONTENT_TYPE_METRICS
        body = resp.read().decode()

    # Shape, not an exact payload: every series carries a TYPE line, and pinning the whole
    # body would make every added metric a test failure.
    assert "# TYPE app_build_info gauge" in body
    assert body.endswith("\n"), "exposition must end with a newline or the last sample is lost"


def test_metrics_reports_the_version_health_reports(monkeypatch: pytest.MonkeyPatch) -> None:
    """`app_build_info` and `app_version()` are the same number, chart-injected value included.

    Two endpoints reading the version from two places is how a dashboard grouped by
    `version` ends up disagreeing with the `/health` response an operator is looking at
    during an incident — the one moment the disagreement costs the most.
    """
    monkeypatch.setenv("APP_VERSION", "7.8.9")

    with serving() as base, urllib.request.urlopen(f"{base}/metrics", timeout=5) as resp:
        body = resp.read().decode()

    assert build_info_version(body) == app_version() == "7.8.9"


def test_metrics_payload_matches_the_served_body() -> None:
    """The handler renders the payload function, so the two cannot drift apart."""
    assert build_info_version(metrics_payload()) == app_version()


def test_unknown_route_is_a_404() -> None:
    """`/metrics` must not have made the handler answer everything.

    A catch-all 200 turns a typo in the ServiceMonitor path into a target that scrapes
    happily and stores nothing parseable, which is precisely the silent failure this
    endpoint exists to avoid.
    """
    with serving() as base, pytest.raises(urllib.error.HTTPError) as excinfo:
        urllib.request.urlopen(f"{base}/nope", timeout=5)

    assert excinfo.value.code == 404
