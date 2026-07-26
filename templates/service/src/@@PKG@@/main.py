"""Worker entrypoint for @@PROJECT@@.

This is a skeleton, but not an empty one: it implements the four parts of the service
runtime contract (standard/profiles/service.md) that CI, the Helm chart and the platform's
cross-service tests all depend on, so that replacing the placeholder message source cannot
accidentally drop one of them.

    1. Configuration comes from the environment ONLY (:class:`Config`). Nothing is read
       from a file baked into the image, because the same image must run unchanged in every
       environment — a file would make dev and prod different artifacts.
    2. ``GET /health`` answers 200 with ``{"status", "version"}`` (:class:`HealthState`),
       even though this process is a worker with no business HTTP surface. The chart renders
       an httpGet probe against it and the platform's tier-(d) tests use it to decide when a
       rollout is finished.
    3. ``GET /metrics`` answers 200 with Prometheus text (:class:`Metrics`), on the SAME
       server and the SAME port as ``/health``. A worker has no request traffic to measure,
       which is exactly why it needs this: with no HTTP surface, the counters below are the
       only evidence outside the log that the loop is still consuming anything. The chart's
       ServiceMonitor scrapes this path, so the handler and the chart flag move together —
       a ServiceMonitor aimed at a path the process does not serve is a scrape target that
       fails silently, leaving empty panels and telling nobody why.
    4. Logs are structured JSON on stdout (:class:`JsonFormatter`). The container runtime
       owns log shipping; a process that writes files needs a writable filesystem, and this
       one deliberately has none.
    5. Shutdown is graceful (:func:`run_worker`): SIGTERM stops *intake*, the in-flight batch
       is finished and committed, and the process exits 0. Exiting non-zero on a normal
       shutdown makes Kubernetes report CrashLoopBackOff for a healthy deployment.

The ordering rule that is easiest to get wrong and hardest to notice: **commit after the
work succeeded, never on receipt**. Auto-commit-on-receipt loses every message that was
in-flight when the pod was killed, silently, with a green dashboard.

Run it with ``python -m @@PKG@@.main``.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import threading
import time
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import FrameType
from typing import Any, Protocol

from . import __version__

LOG = logging.getLogger(__name__)

# The Prometheus text exposition Content-Type, version parameter included. A scraper that
# receives `text/plain` without `version=0.0.4` (or worse, `application/json`) records the
# target as up and the sample as unparseable — a green target with no series behind it.
CONTENT_TYPE_METRICS = "text/plain; version=0.0.4; charset=utf-8"


# ---------------------------------------------------------------------------------------
# Configuration — environment only
# ---------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Config:
    """Everything this process needs to start, read once at startup.

    Frozen on purpose: configuration that can change under a running worker turns every
    incident into "which value was live at the time?". A change of configuration is a new
    pod, which is also how the platform rolls one out.

    Every field here MUST appear in ``docs/configuration.md`` — that table is what an
    operator reads when the ConfigMap and the Secret are assembled, and CI's doc-sync gate
    fails a change that adds a variable without documenting it.
    """

    host: str
    port: int
    version: str
    log_level: str
    poll_interval_seconds: float

    @staticmethod
    def from_env() -> Config:
        """Build the configuration from ``os.environ``, applying documented defaults."""
        return Config(
            # 0.0.0.0 is correct inside a container: the health server must be reachable
            # from the kubelet on the pod IP, and exposure is decided by the Service and the
            # HTTPRoute, not by the bind address. `# nosec` silences bandit B104, which
            # cannot see that boundary.
            host=os.environ.get("APP_HOST", "0.0.0.0"),  # nosec B104
            port=_env_int("APP_PORT", 8080),
            # Set by the chart from .Chart.AppVersion, i.e. the released SemVer. See
            # __init__.py for why the package constant is only a fallback.
            version=os.environ.get("APP_VERSION", __version__),
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
            poll_interval_seconds=_env_float("POLL_INTERVAL_SECONDS", 1.0),
        )


def _env_int(name: str, default: int) -> int:
    """Read an int from the environment, failing loudly on garbage.

    A typo in a ConfigMap must stop the pod at startup with a readable message rather than
    silently fall back to a default: a service running on the wrong port because someone
    wrote ``APP_PORT: "80 80"`` is far more expensive to diagnose than a CrashLoop with
    "invalid APP_PORT" in the log.
    """
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise SystemExit(f"invalid {name}={raw!r}: expected an integer") from exc


def _env_float(name: str, default: float) -> float:
    """Read a float from the environment. See :func:`_env_int` for the failure policy."""
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise SystemExit(f"invalid {name}={raw!r}: expected a number") from exc


# ---------------------------------------------------------------------------------------
# Logging — structured, stdout, no secrets
# ---------------------------------------------------------------------------------------
class JsonFormatter(logging.Formatter):
    """One JSON object per line, so the log aggregator needs no per-service parser.

    Deliberately hand-rolled instead of pulling a logging library: a library here becomes a
    dependency of the image, of the SBOM and of every CVE triage, in exchange for ~10 lines.

    Never log a payload wholesale — a message body is exactly where a token ends up.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str) -> None:
    """Send structured logs to stdout.

    stdout, not stderr and not a file: the container runtime collects stdout, and a
    read-only root filesystem has nowhere to put a log file anyway. ``force=True`` so that a
    library that already called ``basicConfig`` at import time cannot win.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)


# ---------------------------------------------------------------------------------------
# Metrics — Prometheus text exposition
# ---------------------------------------------------------------------------------------
@dataclass
class Metrics:
    """The counters this worker maintains, rendered on demand as Prometheus text.

    Hand-rolled rather than pulling a client library, for the same reason as
    :class:`JsonFormatter`: a dependency here lands in the image, in the SBOM and in every
    CVE triage, in exchange for a few lines of string formatting. Swap in a real client
    library the moment you need histograms — quantiles are where hand-rolling stops paying.

    **Every counter here is one the worker actually increments.** A metric that is wired to
    nothing reports a steady zero, which is indistinguishable from "nothing is happening" —
    the single most expensive kind of wrong, because an alert built on it never fires.

    ``received`` and ``committed`` are two counters rather than one on purpose: their
    difference is the commit-after-success invariant made observable. A persistent gap means
    work is being taken and not acknowledged, which is the shape of a poison message; the two
    numbers moving together is the only external evidence the loop is healthy.
    """

    started_at: float = field(default_factory=time.monotonic)
    received: int = 0
    committed: int = 0
    # The worker loop and the HTTP thread touch these concurrently: `+=` on an int is a read
    # and a write, and a counter that quietly undercounts is worse than no counter at all.
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record_received(self, count: int) -> None:
        with self.lock:
            self.received += count

    def record_committed(self, count: int = 1) -> None:
        with self.lock:
            self.committed += count

    def render(self, version: str) -> str:
        """The exposition body. ``version`` is what ``/health`` reports, so they cannot drift.

        Every label value comes from a fixed, tiny set. A label carrying an unbounded value —
        a message key, a user id, a raw error string — multiplies series until the metrics
        backend degrades and takes the dashboards of every other service with it. Unbounded
        values are log fields, never metric labels.
        """
        with self.lock:
            received, committed = self.received, self.committed
        uptime = time.monotonic() - self.started_at
        return (
            "# HELP app_build_info Build information; the value is always 1.\n"
            "# TYPE app_build_info gauge\n"
            f'app_build_info{{version="{version}"}} 1\n'
            "# HELP app_uptime_seconds Seconds since this process started.\n"
            "# TYPE app_uptime_seconds gauge\n"
            f"app_uptime_seconds {uptime:.3f}\n"
            "# HELP app_messages_received_total Messages taken from the source.\n"
            "# TYPE app_messages_received_total counter\n"
            f"app_messages_received_total {received}\n"
            "# HELP app_messages_committed_total Messages acknowledged after processing.\n"
            "# TYPE app_messages_committed_total counter\n"
            f"app_messages_committed_total {committed}\n"
        )


# One registry per process, like the global registry every Prometheus client library ships.
# The alternative — threading an instance through every call site — looks tidier right up to
# the first caller that forgets, and that caller's numbers stay at zero with nothing to show
# for it. Tests that need isolation pass their own :class:`Metrics` explicitly.
METRICS = Metrics()


# ---------------------------------------------------------------------------------------
# Health and metrics endpoints
# ---------------------------------------------------------------------------------------
@dataclass
class HealthState:
    """What ``/health`` reports. Shared between the worker thread and the HTTP thread."""

    version: str
    stop: threading.Event = field(default_factory=threading.Event)

    def payload(self) -> dict[str, str]:
        """The response body. ``status`` and ``version`` are the contract's minimum."""
        return {
            "status": "draining" if self.stop.is_set() else "ok",
            "version": self.version,
        }


class HealthHandler(BaseHTTPRequestHandler):
    """Serves the two endpoints the runtime contract requires, and nothing else.

    ``GET /health`` → JSON, ``GET /metrics`` → Prometheus text. One server on one port: a
    worker has no business HTTP surface, so a second listener would mean a second container
    port, a second Service port and a second thing to get wrong in the chart, all to separate
    two handlers that answer the same three callers (the kubelet, the scraper, tier-(d)).

    ``state`` and ``metrics`` are injected by :func:`start_health_server` through a subclass,
    because ``BaseHTTPRequestHandler`` is instantiated per request by the server and has no
    other way to receive dependencies.
    """

    state: HealthState
    metrics: Metrics
    # Answer HTTP/1.1 so probes can keep the connection alive; the default HTTP/1.0 makes
    # each probe a fresh TCP connection and shows up as socket churn under a 1s period.
    protocol_version = "HTTP/1.1"

    # The camelCase name is mandated by BaseHTTPRequestHandler's dispatch (it looks up
    # "do_" + the HTTP verb), so it is not ours to rename.
    def do_GET(self) -> None:
        route = self.path.split("?", 1)[0]
        if route == "/health":
            # 200 even while draining, and the caller learns the real state from `status`.
            # A failing liveness probe during termination gets the container KILLED, which is
            # precisely the graceful shutdown this service is trying to perform.
            body = json.dumps(self.state.payload()).encode("utf-8")
            self._respond(HTTPStatus.OK, "application/json", body)
        elif route == "/metrics":
            # The version rendered here is the one /health reports — same source, so a
            # dashboard grouping by `version` and a probe response can never disagree.
            body = self.metrics.render(self.state.version).encode("utf-8")
            self._respond(HTTPStatus.OK, CONTENT_TYPE_METRICS, body)
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def _respond(self, status: HTTPStatus, content_type: str, body: bytes) -> None:
        """One write path for every route, so no response can forget Content-Length.

        Under HTTP/1.1 keep-alive a missing Content-Length is not a cosmetic omission: the
        client waits for a body terminator that never comes and the probe times out.
        """
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # `format` shadows the builtin, but the parameter NAME is part of the signature mypy
    # checks against the superclass — renaming it makes this an incompatible override.
    def log_message(self, format: str, *args: Any) -> None:
        """Route the stdlib's access log into our structured logger, at DEBUG.

        The default implementation writes unformatted text straight to stderr, which breaks
        the one-JSON-object-per-line promise; and a probe every second at INFO would drown
        every real event in the log.
        """
        LOG.debug("http request: " + format, *args)


def start_health_server(
    cfg: Config, state: HealthState, metrics: Metrics = METRICS
) -> ThreadingHTTPServer:
    """Start the health/metrics server on a daemon thread and return it.

    A separate thread because the worker loop owns the main thread and must stay responsive
    to signals; a daemon thread because a hung HTTP thread must never be the reason a
    terminating pod has to be SIGKILLed.
    """
    handler = type("BoundHealthHandler", (HealthHandler,), {"state": state, "metrics": metrics})
    server = ThreadingHTTPServer((cfg.host, cfg.port), handler)
    thread = threading.Thread(target=server.serve_forever, name="health", daemon=True)
    thread.start()
    LOG.info("http endpoints listening on %s:%s (/health, /metrics)", cfg.host, cfg.port)
    return server


# ---------------------------------------------------------------------------------------
# Message intake — receive, process, THEN commit
# ---------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Message:
    """One unit of work. ``key`` is what makes reprocessing idempotent."""

    key: str
    payload: dict[str, Any]


class Source(Protocol):
    """The broker-shaped interface the worker needs; implement it over the real client.

    Split into ``receive`` and ``commit`` on purpose. A client configured to auto-commit on
    receipt cannot implement this protocol honestly, and that is the point: the type system
    makes the losing design awkward to express.
    """

    def receive(self, timeout: float) -> list[Message]:
        """Return the next batch (possibly empty) without acknowledging anything."""
        ...

    def commit(self, message: Message) -> None:
        """Acknowledge one message as durably processed."""
        ...


class NullSource:
    """Placeholder source that never yields work — replace with the real client.

    It exists so the skeleton is runnable end to end (the image boots, /health answers, the
    shutdown path is exercised) before any broker is wired in, which is what
    ``auto-tests/group-a/validate-deploy.sh`` verifies on every pipeline.
    """

    def receive(self, timeout: float) -> list[Message]:
        # Sleep for the same duration a real long-poll would block, so the loop's timing
        # (and its CPU profile) does not change when a real client is dropped in.
        time.sleep(timeout)
        return []

    def commit(self, message: Message) -> None:
        LOG.debug("commit %s", message.key)


def handle_message(message: Message) -> None:
    """Process one message. Replace with the real work.

    MUST be idempotent: at-least-once delivery plus a crash between processing and commit
    means this function will eventually be called twice with the same ``key``. Idempotency
    is the only thing that turns that from data corruption into a no-op.
    """
    LOG.info("processing message %s", message.key)


def run_worker(
    source: Source, cfg: Config, stop: threading.Event, metrics: Metrics = METRICS
) -> None:
    """Consume until ``stop`` is set, committing only what actually succeeded.

    The shutdown semantics are the interesting part:

    * ``stop`` is checked before FETCHING, so SIGTERM stops intake immediately;
    * the batch already in hand is finished and committed, so no in-flight work is lost;
    * a message that raises is NOT committed and will be redelivered — losing it silently
      would be worse than reprocessing it, which :func:`handle_message` is idempotent for.

    The two counter calls mirror that ordering exactly, which is what makes ``/metrics``
    worth scraping: ``received`` rises when work is taken, ``committed`` only once it is
    done, so a widening gap on a dashboard IS the stuck-message symptom, visible before
    anyone reads a log.
    """
    LOG.info("worker started")
    while not stop.is_set():
        batch = source.receive(cfg.poll_interval_seconds)
        metrics.record_received(len(batch))
        for message in batch:
            handle_message(message)
            # After, never before: a crash on the line above must leave the message
            # uncommitted so the broker redelivers it.
            source.commit(message)
            metrics.record_committed()
    LOG.info("worker stopped: intake closed, in-flight work committed")


# ---------------------------------------------------------------------------------------
# Process lifecycle
# ---------------------------------------------------------------------------------------
def install_signal_handlers(stop: threading.Event) -> None:
    """Translate SIGTERM/SIGINT into "stop taking new work".

    SIGTERM is what Kubernetes sends first; the grace period that follows is the budget for
    finishing the current batch. The handler only sets an Event — doing real work inside a
    signal handler (I/O, locks, commits) is how shutdown deadlocks are born.
    """

    def _handle(signum: int, _frame: FrameType | None) -> None:
        LOG.info("received signal %s: draining", signal.Signals(signum).name)
        stop.set()

    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)


def main() -> int:
    """Wire everything together. Returns the process exit code."""
    cfg = Config.from_env()
    configure_logging(cfg.log_level)
    LOG.info("starting @@PROJECT@@ version=%s", cfg.version)

    state = HealthState(version=cfg.version)
    install_signal_handlers(state.stop)
    server = start_health_server(cfg, state)

    try:
        run_worker(NullSource(), cfg, state.stop)
    except Exception:
        # Log the traceback through the structured logger (so it is one aggregatable event)
        # and exit non-zero — a real failure, unlike shutdown, SHOULD restart the pod.
        LOG.exception("worker failed")
        return 1
    finally:
        server.shutdown()
        server.server_close()

    LOG.info("shutdown complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
