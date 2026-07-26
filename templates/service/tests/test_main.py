"""Tier-(a) unit tests for the runtime contract of @@PROJECT@@.

These assert the promises that the chart, CI and the platform's cross-service tests build
on — configuration from the environment, the /health payload shape, the /metrics exposition
the ServiceMonitor scrapes, commit-after-success ordering, and "SIGTERM stops intake but
finishes the batch in hand". They run in CI through /lint.yml (pytest, on the 3.11 and 3.12
legs); the container-level proof of the same contract lives in
auto-tests/group-a/validate-deploy.sh.

Written before the implementation, per the TDD rule in CLAUDE.md: a test added after the
code passes tends to assert what the code does rather than what it must do.
"""

from __future__ import annotations

import contextlib
import json
import re
import threading
import urllib.request
from collections.abc import Iterator

import pytest

from @@PKG@@.main import (
    CONTENT_TYPE_METRICS,
    Config,
    HealthState,
    Message,
    Metrics,
    NullSource,
    run_worker,
    start_health_server,
)


def test_config_defaults_come_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """No environment, documented defaults. Every default here is in docs/configuration.md."""
    for name in ("APP_HOST", "APP_PORT", "APP_VERSION", "LOG_LEVEL", "POLL_INTERVAL_SECONDS"):
        monkeypatch.delenv(name, raising=False)

    cfg = Config.from_env()

    assert cfg.host == "0.0.0.0"
    assert cfg.port == 8080
    assert cfg.log_level == "INFO"


def test_config_reads_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_PORT", "9090")
    monkeypatch.setenv("APP_VERSION", "1.2.3")
    monkeypatch.setenv("LOG_LEVEL", "debug")

    cfg = Config.from_env()

    assert cfg.port == 9090
    assert cfg.version == "1.2.3"
    # Upper-cased, so LOG_LEVEL=debug (how a human writes it) is accepted by `logging`.
    assert cfg.log_level == "DEBUG"


def test_invalid_numeric_config_stops_the_process(monkeypatch: pytest.MonkeyPatch) -> None:
    """A typo in a ConfigMap must fail loudly at startup, not fall back to a default."""
    monkeypatch.setenv("APP_PORT", "80 80")

    with pytest.raises(SystemExit):
        Config.from_env()


def test_health_payload_has_status_and_version() -> None:
    """The minimum body the service profile mandates: {"status", "version"}."""
    state = HealthState(version="1.2.3")

    payload = state.payload()

    assert payload["status"] == "ok"
    assert payload["version"] == "1.2.3"


def test_health_payload_reports_draining_after_sigterm() -> None:
    """Still a 200 body, but a caller can see the pod is going away."""
    state = HealthState(version="1.2.3")
    state.stop.set()

    assert state.payload()["status"] == "draining"


@contextlib.contextmanager
def serving(version: str = "1.2.3", metrics: Metrics | None = None) -> Iterator[str]:
    """Run the real endpoint server on an ephemeral port and yield its base URL.

    Port 0 rather than a fixed one: a hardcoded port turns two tests running in parallel — or
    one machine with something already on 8080 — into a flake that looks like a code failure.

    Exercised over HTTP rather than by calling ``Metrics.render()`` directly, because the
    Content-Type a scraper depends on is set by the handler, not by the renderer. A test that
    only calls the renderer stays green while the endpoint answers with the wrong header,
    which is exactly the failure that shows up as a target Prometheus marks UP and stores
    nothing from.
    """
    cfg = Config(
        host="127.0.0.1", port=0, version=version, log_level="INFO", poll_interval_seconds=0.0
    )
    state = HealthState(version=cfg.version)
    server = start_health_server(cfg, state, metrics if metrics is not None else Metrics())
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def test_metrics_endpoint_answers_200_in_prometheus_exposition_format() -> None:
    """The whole of what the ServiceMonitor needs: a 200, the right header, a parseable body.

    SHAPE, NOT AN EXACT PAYLOAD — the same invariant, and the same reasoning, as the
    container-level probe in auto-tests/group-a/validate-deploy.sh. Every Prometheus
    exposition carries ``# TYPE`` lines; pinning the body instead would turn each added
    metric into a test failure and teach whoever hits it to delete the assertion. What this
    does catch is the case that matters: a 200 whose body is JSON, HTML or an error page.
    """
    with serving() as base, urllib.request.urlopen(f"{base}/metrics", timeout=5) as resp:
        assert resp.status == 200
        assert resp.headers["Content-Type"] == CONTENT_TYPE_METRICS
        body = resp.read().decode()

    assert "# TYPE " in body, f"not Prometheus exposition:\n{body}"
    assert body.endswith("\n"), "exposition must end with a newline or the last sample is lost"


def test_metrics_reports_the_version_health_reports() -> None:
    """One version, two endpoints, one source.

    Two endpoints reading the version from two places is how a dashboard grouped by
    ``version`` ends up disagreeing with the ``/health`` response an operator is reading
    during an incident — the one moment the disagreement costs the most.
    """
    with serving(version="4.5.6") as base:
        with urllib.request.urlopen(f"{base}/health", timeout=5) as resp:
            health_version = json.loads(resp.read())["version"]
        with urllib.request.urlopen(f"{base}/metrics", timeout=5) as resp:
            exposition = resp.read().decode()

    match = re.search(r'^app_build_info\{version="([^"]+)"\} 1$', exposition, re.MULTILINE)
    assert match, f"no app_build_info series in:\n{exposition}"
    assert match.group(1) == health_version == "4.5.6"


def _config() -> Config:
    """A config whose only interesting property is a zero poll interval (fast tests)."""
    return Config(
        host="127.0.0.1", port=0, version="test", log_level="INFO", poll_interval_seconds=0.0
    )


class RecordingSource:
    """A :class:`Source` that records the exact order of receive/commit calls.

    The ordering assertions below are the reason this class exists: nothing else in the
    stack catches an auto-commit-on-receipt regression, and in production it surfaces months
    later as "a few messages went missing after a restart".

    ``stop`` is set once the batches run out, which is how the worker loop is made to
    terminate in a unit test — the real loop only ever exits on a signal.
    """

    def __init__(
        self,
        batches: list[list[Message]],
        stop: threading.Event,
        stop_on_commit: str | None = None,
    ) -> None:
        self._batches = list(batches)
        self._stop = stop
        self._stop_on_commit = stop_on_commit
        self.events: list[str] = []

    def receive(self, timeout: float) -> list[Message]:
        if not self._batches:
            self._stop.set()
            return []
        batch = self._batches.pop(0)
        self.events.extend(f"receive:{message.key}" for message in batch)
        return batch

    def commit(self, message: Message) -> None:
        self.events.append(f"commit:{message.key}")
        if self._stop_on_commit == message.key:
            # Simulates SIGTERM arriving in the middle of a batch.
            self._stop.set()


def test_worker_commits_only_after_processing() -> None:
    stop = threading.Event()
    source = RecordingSource([[Message("a", {}), Message("b", {})]], stop)

    run_worker(source, _config(), stop)

    # Both messages are received before either is committed, and every commit follows its
    # own processing. A source that acknowledged on receipt would interleave differently.
    assert source.events == ["receive:a", "receive:b", "commit:a", "commit:b"]


def test_metrics_counters_are_wired_to_the_worker() -> None:
    """The counters /metrics exposes move when work moves, rather than reporting a flat zero.

    This is what stops the endpoint above from being a well-formed lie. A metric wired to
    nothing renders perfectly, passes every shape assertion, and reports a steady zero that
    is indistinguishable from "nothing is happening" — the most expensive kind of wrong,
    because an alert built on it never fires. ``received`` and ``committed`` in particular are
    the commit-after-success invariant made observable: a persistent gap between them is the
    external symptom of a poison message.

    An explicit Metrics instance, not the module-global METRICS: a test asserting exact
    counts against a registry other tests also increment is order-dependent by construction.
    """
    metrics = Metrics()
    stop = threading.Event()
    source = RecordingSource([[Message("a", {}), Message("b", {})]], stop)

    run_worker(source, _config(), stop, metrics)

    exposition = metrics.render("1.2.3")
    assert "app_messages_received_total 2" in exposition
    assert "app_messages_committed_total 2" in exposition


def test_worker_finishes_the_in_flight_batch_after_stop() -> None:
    """SIGTERM stops intake; it does not abandon work already received."""
    stop = threading.Event()
    source = RecordingSource([[Message("a", {}), Message("b", {})]], stop, stop_on_commit="a")

    run_worker(source, _config(), stop)

    assert source.events == ["receive:a", "receive:b", "commit:a", "commit:b"]


def test_worker_does_not_open_intake_when_already_stopping() -> None:
    """A stop set before the loop starts must not fetch anything at all."""
    stop = threading.Event()
    stop.set()
    source = RecordingSource([[Message("a", {})]], stop)

    run_worker(source, _config(), stop)

    assert source.events == []


def test_null_source_yields_no_work() -> None:
    """The placeholder source lets the skeleton boot and shut down before a broker exists."""
    assert NullSource().receive(0.0) == []
