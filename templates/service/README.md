# @@PROJECT@@

@@DESCRIPTION@@

One deployable process, following the **service** profile of the shared standard
(`standard/profiles/service.md`). It publishes exactly two artifacts from one commit — a
container image and a Helm chart, at the same version — and it never deploys itself.

| | |
|---|---|
| Image | `<registry>/@@GROUP@@/@@PROJECT@@` |
| Chart (OCI) | `oci://<registry>/<group>/charts/@@PROJECT@@` |
| Entrypoint | `python -m @@PKG@@.main` |
| Rules | [`CLAUDE.md`](CLAUDE.md) — generated from `standard/`, read it before changing anything |

## Features

> User-facing product features only — what this service does for whoever consumes it.
> Engineering and infrastructure work belongs in [`CHANGELOG.md`](CHANGELOG.md), and
> not-yet-built ideas in [`TODO.md`](TODO.md). A feature lands here **when it ships**.

- **Health endpoint.** `GET /health` returns `200` with `{"status", "version"}`, so
  orchestration and the platform's cross-service tests can tell a live instance from a
  starting one, and can see which released version is actually running.
- _Add the first real feature here once it ships._

## Adopting this scaffold

1. Replace every placeholder: `@@PROJECT@@` (hyphenated repo/image/chart name), `@@PKG@@`
   (underscored Python package, also the `src/@@PKG@@/` directory), `@@PREFIX@@` (ticket
   prefix), `@@GROUP@@` (GitLab namespace), `@@DESCRIPTION@@`,
   `@@CI_TEMPLATES_PROJECT@@` (the shared CI templates repo, as a GitLab project path),
   `@@CI_TEMPLATES_REF@@` (the tag of it to pin) and `@@RUNNER_TAG@@` (the tag of your
   runner fleet — it appears in four blocks of `.gitlab-ci.yml` that must stay in sync).
   `grep -rnE '@{2}' .` must come back empty when you are done.
2. Run `./standard/compose.sh` to generate `CLAUDE.md`, and commit it.
3. Set `next-version` in `GitVersion.yml` to the first version you intend to release.
4. Push to `dev` and read the pipeline logs — including the green jobs.

## Layout

```
src/@@PKG@@/          application code; entrypoint is main.py
deploy/Dockerfile     the image (the shared CI default path — no override needed)
helm/                 the chart (likewise the default path)
auto-tests/group-a/   tier-(a) scripts CI runs against the built image
auto-tests/group-b/   tier-(b) sandbox scenarios, run by the agent
auto-tests/group-c/   tier-(c) methodologies, handed to a human
tests/                pytest suite, run by the shared Python gate
docs/                 architecture, configuration, tests, contracts
.versions/            WRITTEN BY CI — the interface to the platform repo
standard/             the shared rulebook's sources + this repo's identity
```

## Local development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'

pytest                       # tier-(a) unit tests
ruff check src tests         # same linter CI runs
mypy src tests               # same type gate CI runs

APP_PORT=8080 python -m @@PKG@@.main
curl -s localhost:8080/health
```

Run the container exactly as the cluster will — read-only root filesystem, non-root uid,
no capabilities — which is what the tier-(a) script does on every pipeline:

```bash
docker build -f deploy/Dockerfile -t @@PROJECT@@:dev .
docker run --rm --read-only --tmpfs /tmp --user 10001:10001 --cap-drop ALL \
  -p 8080:8080 @@PROJECT@@:dev

./auto-tests/group-a/validate-deploy.sh   # the full smoke test, locally
```

Render the chart without a cluster:

```bash
helm template @@PROJECT@@ helm --set image.tag=dev
helm lint helm
```

## CI/CD

`.gitlab-ci.yml` is a **composition** of the shared CI templates repo, pinned to a tag —
there are no inline jobs, and new shared CI logic belongs in that repo rather than here. The
pipeline versions (GitVersion), lints and type-checks, scans (checkov / trivy / gitleaks /
semgrep / bandit / pip-audit / hadolint), builds and signs the image, packages the chart at
the same SemVer, runs `auto-tests/group-a/*.sh` against the built image, and commits
`.versions/*.env` back.

It never touches a cluster. See `docs/architecture.md` for the deployment shape.

## Releasing

Releasing is a **merge**, not a tag: `dev` → a `-dev` build, `rc` → a pre-release,
`release` → the stable version. Each is approval-gated, and each publishes the image and the
chart at the same `GitVersion_SemVer`.

Deploying is a separate, explicit act **in the platform repo**: bump `chartVersion` in the
target environment's `bundle.yaml`. That MR is the deployment; reverting it is the rollback.
