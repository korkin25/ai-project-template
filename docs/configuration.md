# Configuration — environment variables

Everything the service needs at runtime is configured through environment variables, never a
file baked into the image — an image that carries its own config is an image that has to be
rebuilt to move between environments. Nothing sensitive is committed; secrets arrive from the
environment: locally from Docker/compose, in the cluster by reference to an existing Secret
via the chart's `envFrom.secret`, and in CI from the host's own variable store (see
*CI functional tests* below).

Update this file **in the same change** whenever you add or rename a runtime env var
(Documentation-sync rule).

## Sample app (`app-serve`)

| Variable | Default | Secret | Purpose |
|----------|---------|:------:|---------|
| `APP_HOST` | `0.0.0.0` | | Bind host for the HTTP service. |
| `APP_PORT` | `8080` | | Bind port for the HTTP service. |

## Tests

| Variable | Default | Purpose |
|----------|---------|---------|
| `APP_LIVE` | unset | Set to `1` to enable any gated live tests you add. |

## CI functional tests

**The concept, which is the same on every host:** the `functional` job boots the image CI just
built and drives it from outside, so it needs the same variables the container needs at
runtime. Those live in the CI host's variable store, scoped as narrowly as the host allows —
never in the repository, and never inlined into the pipeline file, where a value becomes both
unreviewable and permanent.

What this repo's job needs:

- **Variable** `APP_PORT` — the port the functional job probes (default `8080`).
- **Secrets** — none for the sample. Add yours here as your service grows, and keep the job
  guarded so it **skips cleanly** when a secret is absent. Forks and freshly-cloned repos have
  no secrets by definition; a job that hard-fails there is a permanently red check that
  everyone learns to scroll past, which costs more than the test was worth.

**The mechanics, which differ.** The standard takes no side; a project picks one host and
records it in [architecture.md](architecture.md).

| | GitLab | GitHub |
|---|---|---|
| Where values live | project (or group) CI/CD variables | repository or organization variables |
| Scoping | an **environment scope** on the variable (`ci-functional`) | an **environment** named `ci-functional`, holding its own variables |
| Secret vs plain | one store; a secret is a variable marked **masked** (and usually **protected**) | two stores — variables and secrets — with secrets write-only after creation |
| Set a variable | `glab variable set APP_PORT 8080 --scope ci-functional` | `gh variable set APP_PORT --env ci-functional --body "8080"` |
| Set a secret | `glab variable set MY_TOKEN --masked --protected --scope ci-functional` | `gh secret set MY_TOKEN --env ci-functional` |

Both secret commands read the value from **stdin** when none is given on the command line, so
the token never lands in your shell history.
| Read it in a job | `$APP_PORT` | `${{ vars.APP_PORT }}` / `${{ secrets.MY_TOKEN }}` |

The difference worth knowing is the last one in the "secret vs plain" row. GitHub keeps
secrets in a separate, write-only store, so a wrong value is replaced rather than inspected.
GitLab keeps everything in one place and *masking is opt-in* — an unmasked secret is a normal
variable that will be echoed into a job log the first time something prints the environment.
Set `masked` when you create it, not after: the log that already leaked it is not retroactively
redacted.
