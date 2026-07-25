# Configuration — environment variables

Everything the service needs at runtime is configured through environment variables. Nothing
sensitive is committed; secrets come from the environment (locally from Docker/compose or the
Helm chart's `envFrom.secret`; in CI from the GitHub Actions environment `ci-functional`).

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

The `functional` CI job boots the built image and probes `/health`. It reads a minimal set
from the GitHub Actions environment **`ci-functional`**:

- **Variable** `APP_PORT` — the port the functional job probes (default `8080`).
- **Secrets** — none for the sample. Add yours here as your service grows, and keep the job
  guarded so it **skips cleanly** when a secret is absent (forks and unconfigured repos stay
  green).

Set them with:

```bash
gh variable set APP_PORT --env ci-functional --body "8080"
# gh secret set MY_TOKEN --env ci-functional   # paste when prompted
```
