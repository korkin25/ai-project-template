# Configuration — @@PROJECT@@

Every runtime setting arrives as an **environment variable**. Nothing is read from a file
baked into the image, because the same image must run unchanged in every environment — a
config file inside the image makes dev and prod different artifacts, and then "it works in
dev" stops being evidence of anything.

**Update this file in the same change as the code.** CI's doc-sync gate fails a change that
adds or renames a variable without touching this table, and an undocumented variable is one
an operator cannot set — it is not configuration, it is a hidden default.

## Where the values come from

| Environment | Source |
|---|---|
| Cluster (non-secret) | namespace-wide `ConfigMap` (`platform-config`), mounted via `envFrom` |
| Cluster (secret) | per-service `Secret` (`@@PROJECT@@-secrets`), provisioned by the secrets operator, referenced by name — **never templated by the chart** |
| Cluster (version) | `APP_VERSION`, injected by the chart from `.Chart.AppVersion` |
| Local | your shell, or a `.env` that is git-ignored |
| CI | the pipeline environment; the functional job sets only what the smoke test needs |

## Variables

| Variable | Default | Secret | Purpose |
|---|---|:---:|---|
| `APP_HOST` | `0.0.0.0` | | Bind address of the health server. `0.0.0.0` is correct inside a container: reachability is decided by the Service and the HTTPRoute, not by the bind address. |
| `APP_PORT` | `8080` | | Port of the health server. The chart sets it from `service.port`, so the container port and the probe never disagree. |
| `APP_VERSION` | package `__version__` (`0.0.0`) | | The version reported by `/health`. Set by the chart from the released SemVer; the fallback only appears when someone runs the image by hand. |
| `LOG_LEVEL` | `INFO` | | Log level; accepted case-insensitively. `DEBUG` also logs one line per health probe. |
| `POLL_INTERVAL_SECONDS` | `1.0` | | How long one intake fetch may block. Also the worst-case delay between SIGTERM and the loop noticing it. |

<!-- Add each new variable here in the same change that introduces it:
| `EXAMPLE_URL` | _(required)_ | | Endpoint of … . No default on purpose: a wrong-but-plausible default is worse than a startup failure. |
-->

## Failure policy

A malformed numeric value **stops the process at startup** with a message naming the
variable, rather than falling back to the default. A service silently running on the wrong
port because a ConfigMap says `"80 80"` is far more expensive to diagnose than a pod that
refuses to start and says why.

## Secrets

- Never committed, never logged, never rendered by the chart into a manifest.
- The chart references an existing `Secret` by name; creating it is the platform's or the
  infra repo's job, and the procedure that seeds it belongs in their docs.
- Treat any token seen in this repo's environment as a full-access credential: rotate it if
  it was ever printed.
