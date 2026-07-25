# Test plan

Per-feature test catalog. When a feature is picked up (after its design is fixed), add a
section here listing its concrete tests **before** writing code — see the Testing policy in
[../CLAUDE.md](../CLAUDE.md). Each test is tagged by group:

- **(a) Fully automated** — runs in GitHub Actions CI on every push/PR. Scripts live in
  [../auto-tests/](../auto-tests/) and/or the `tests/` suite. The agent analyses the CI run
  logs even when green.
- **(b) Dev-machine / AI-sandbox** — runnable only on a developer machine or against external
  services, or not fully automatable; run in an isolated sandbox under the agent's control.
- **(c) Human-in-the-loop** — needs a human; the agent writes a methodology and hands it over.

Per-test pass/fail status for the **current** feature is tracked in [../TODO.md](../TODO.md);
a feature is done only when 100% of its tests pass (group-(c) methodology proposed).

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
-->
