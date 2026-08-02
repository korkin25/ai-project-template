# auto-tests

Structured home for **all** test scripts, scenarios, and methodologies across the three test
groups defined in [../CLAUDE.md](../CLAUDE.md) (Testing policy). The catalog of what each
covers, per feature, lives in [../docs/tests.md](../docs/tests.md).

```
auto-tests/
  group-a/   # fully automated — wired into GitHub Actions CI, run on every push/PR
  group-b/   # dev-machine / AI-sandbox scenarios (external services, hard-to-automate)
  group-c/   # human-in-the-loop methodologies (step-by-step docs for the user)
```

Rules:

- Group-(a) scripts must run headless in CI. The agent reads the CI logs even when green.
- Group-(b)/(c) scenarios are **also used during development**, not only after release.
- The bulk of automated coverage lives in the top-level `tests/` (pytest) suite;
  `auto-tests/group-a/` holds end-to-end / scenario scripts that complement it and any glue
  CI invokes directly (see `validate-deploy.sh`).

## Why one script here is `.bash` and not `.sh`

The shared functional runner discovers `auto-tests/group-a/**/*.sh` **recursively** and maps
exit code 77 to "skipped". That contract is right for `validate-deploy.sh`, which genuinely
cannot run where there is no Docker.

It is wrong for a **security gate**. A scoped "nothing to do" exit is not an exception, it is a
defect to remove: it converts *the scan never ran* into a pass, which is the precise failure a
gate exists to prevent. So `scan-scaffold-charts.bash` deliberately does not match that glob —
it cannot be reported as skipped by anything, it has no skip path of its own (a missing `helm`
or `checkov` is a hard failure), and it is run by its own blocking job in `.gitlab-ci.yml` and
`.github/workflows/ci.yml`.

| File | Runner | On "cannot run here" |
|---|---|---|
| `group-a/validate-deploy.sh` | the shared functional job, by glob | exit 77 → reported skipped |
| `group-a/scan-scaffold-charts.bash` | its own blocking CI job, by name | exit 1 → the pipeline is red |

`group-a/scaffold-chart-values/` holds optional per-chart values overlays for that script, one
file per chart path slug. They are scan fixtures — nothing deploys them.
