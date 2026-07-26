# Test plan

Per-feature test catalog. When a feature is picked up (after its design is fixed), add a
section here listing its concrete tests **before** writing code — see the Testing policy in
[../CLAUDE.md](../CLAUDE.md). Each test is tagged by group:

- **(a) Fully automated** — runs in CI on every push / merge request. Scripts live in
  [../auto-tests/](../auto-tests/) and/or the `tests/` suite. The agent analyses the CI run
  logs even when green. The standard is **host-agnostic**: what makes a test tier-(a) is that
  CI runs it unattended, never which host runs it. A project picks one host, once, and records
  the choice in [architecture.md](architecture.md) — naming a host here instead would push a
  project decision into the test doctrine every repo copies.
- **(b) Dev-machine / AI-sandbox** — runnable only on a developer machine or against external
  services, or not fully automatable; run in an isolated sandbox under the agent's control.
- **(c) Human-in-the-loop** — needs a human; the agent writes a methodology and hands it over.
- **(d) Cross-service end-to-end** — proves this repo works *with the others*. These tests
  **live in the platform repo, not here**, because they need more than one service and a real
  environment; a copy kept locally would assert against mocks and call it integration.
  **This repo is not a platform repo, so it owns no tier-(d) test of its own.** What it owes is
  the other half of the bargain: keeping its side of every contract in
  [contracts.md](contracts.md) drivable from outside — a health endpoint, a deterministic
  fixture, or a documented way to run it. Concretely here that is `GET /health` on the sample
  service, and `standard/compose.sh --check` with its three documented exit codes, which is
  what a consuming repo's drift gate calls. When a change alters a contract, the matching
  tier-(d) test is updated in the platform repo **in the same change set** — a separate MR
  there, linked by the platform id. A contract that moved without its e2e test moving is the
  failure this tier exists to prevent: both repos stay green and the integration is broken.

Per-test pass/fail status for the **current** feature is tracked in [../TODO.md](../TODO.md);
a feature is done only when 100% of its applicable tests pass — every tier covered, the
group-(c) methodology proposed, and group-(d) updated in the platform repo when a contract
moved.

---

## Feature 1 — Sample app (baseline)

| Test | Group | What it asserts | Status |
|------|-------|-----------------|--------|
| `tests/test_app.py::test_version_is_semver` | (a) | version is SemVer | ✅ |
| `tests/test_app.py::test_health_payload` | (a) | health body shape | ✅ |
| `tests/test_app.py::test_server_serves_health` | (a) | server answers `GET /health` 200 | ✅ |
| CI `functional` job boots the image, probes `/health` | (a) | container serves | ✅ |

<!-- Template — copy per new feature:

## Feature <n> — <title>

| Test | Group | What it asserts | Status |
|------|-------|-----------------|--------|
| ... | (a) | ... | ⬜ |
| ... | (b) | ... | ⬜ |
| ... | (c) | ... | ⬜ |
| ... (in the platform repo, linked by its id) | (d) | ... | ⬜ |
-->
