# Test plan — @@PROJECT@@

Per-feature test catalog. When a feature is picked up — after its design is fixed, **before**
any code — add its section here listing the concrete tests, each tagged by tier. See the
Testing policy in [../CLAUDE.md](../CLAUDE.md).

- **(a) Fully automated** — runs in CI on every push/MR. Unit tests in `tests/` (via the
  shared Python gate) and scripts in [`../auto-tests/group-a/`](../auto-tests/group-a/) (via
  `/functional.yml`, against the built image). The agent reads the run logs **even when the
  job is green**.
- **(b) Dev-machine / AI-sandbox** — needs a real dependency or a credential CI does not
  have; run by the agent in a sandbox. See [`../auto-tests/group-b/`](../auto-tests/group-b/).
- **(c) Human-in-the-loop** — needs human judgement; the agent writes the methodology and
  proposes it. See [`../auto-tests/group-c/`](../auto-tests/group-c/).
- **(d) Cross-service end-to-end** — lives in the **platform repo**, not here, because it
  needs more than one service and a real environment. This repo's obligation is to stay
  drivable: a health endpoint, a deterministic fixture, a documented way to feed it. When a
  change moves a contract, the matching tier-(d) test is updated there in the same change
  set, linked by the platform id.

A task is done only when **100 %** of its applicable tiers pass; per-test status for the
feature currently in progress is tracked in [../TODO.md](../TODO.md).

---

## Baseline — runtime contract

These exist from day one and must never regress: everything else in the platform assumes
them.

| Test | Tier | What it asserts | Status |
|---|---|---|---|
| `tests/test_main.py::test_config_defaults_come_from_the_environment` | (a) | config is read from the environment, with the documented defaults | ✅ |
| `tests/test_main.py::test_invalid_numeric_config_stops_the_process` | (a) | a malformed value fails startup instead of falling back | ✅ |
| `tests/test_main.py::test_health_payload_has_status_and_version` | (a) | `/health` body carries at least `status` and `version` | ✅ |
| `tests/test_main.py::test_metrics_endpoint_answers_200_in_prometheus_exposition_format` | (a) | `/metrics` answers `200` with the exposition `Content-Type` and a body carrying `# TYPE` — shape, not an exact payload | ✅ |
| `tests/test_main.py::test_metrics_reports_the_version_health_reports` | (a) | `/metrics` and `/health` report one version, so a dashboard and a probe cannot disagree | ✅ |
| `tests/test_main.py::test_metrics_counters_are_wired_to_the_worker` | (a) | the exposed counters move with the worker instead of reporting a flat zero | ✅ |
| `tests/test_main.py::test_worker_commits_only_after_processing` | (a) | commit happens **after** successful processing, never on receipt | ✅ |
| `tests/test_main.py::test_worker_finishes_the_in_flight_batch_after_stop` | (a) | SIGTERM closes intake but does not abandon received work | ✅ |
| `auto-tests/group-a/validate-deploy.sh` | (a) | the built image boots read-only as uid 10001, serves `/health` and `/metrics`, and exits 0 on SIGTERM | ✅ |
| Chart renders and packages (`/helm-package.yml`) | (a) | the chart is valid at the released SemVer | ✅ |

<!-- Template — copy per new feature:

## Feature <n> — <title>

| Test | Tier | What it asserts | Status |
|---|---|---|---|
| … | (a) | … | ⬜ |
| … | (b) | … | ⬜ |
| … | (c) | methodology proposed to the user | ⬜ |
| platform repo: … | (d) | … (link the platform id) | ⬜ |
-->
