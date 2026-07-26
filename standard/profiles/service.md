
---

# Profile: service

A **service** is one deployable process. It builds exactly one image and one Helm chart,
released together under one version. It never deploys itself and never references another
service's version.

## Layout (canonical)

```
src/@@PKG@@/            application code; entrypoint is `python -m @@PKG@@.main`
deploy/Dockerfile       the image
helm/                   the chart: Chart.yaml, values.yaml, templates/
auto-tests/group-a/     tier-(a) scripts CI discovers and runs (*.sh)
auto-tests/group-b/     tier-(b) scenarios, run by the agent in a sandbox
auto-tests/group-c/     tier-(c) methodologies, handed to a human
docs/                   architecture.md, configuration.md, tests.md, contracts.md
.versions/              WRITTEN BY CI — never hand-edit
```

`deploy/Dockerfile` and `helm/` are the shared templates' defaults, so a service needs **no**
`DOCKERFILE`/`CHART_PATH` overrides in its CI. A repo that deviates must say why in
`docs/architecture.md`.

## CI

The pipeline is **composition, not inline jobs** — every job comes from the shared templates.
**New shared CI logic belongs in the templates repo, never in this repo.**

**GitLab** (`.gitlab-ci.yml`) includes, from `open_ci_cd/templates`:

| Include | Gives |
|---|---|
| `/globals.yml` | stages, runner tags, shared variables, change-detection rules |
| `/auto-semversioning.yml` | `get_unique_semversion` → `GitVersion_SemVer` for the whole pipeline |
| `/lint.yml` | language gates; each self-activates on its marker file. For Python: ruff + mypy + pytest over a 3.11/3.12 matrix, plus radon/xenon complexity |
| `/sast.yml` | checkov, trivy, gitleaks, semgrep, bandit, pip-audit, hadolint |
| `/docker-build.yml` | build + push + cosign signature + SBOM; writes `.versions/docker-image.env` |
| `/helm-package.yml` | packages the chart at the same SemVer, pushes to OCI; writes `.versions/helm-chart.env` |
| `/functional.yml` | runs `auto-tests/group-a/*.sh` against the built image |
| `/commit_changes.yml` | commits the `.versions/*.env` files back with `[skip ci]` |

**On pinning `ref:`.** A tag makes pipelines reproducible and turns a template upgrade into a
deliberate, per-repo act. A moving branch does the opposite: one upstream commit changes the
pipeline in every repository at once, including the ones that were green a minute ago.

This platform currently tracks `main` **by deliberate choice** — the templates repo has no
usable tag (its only tag trails `main` by hundreds of commits and lacks most of the files
included here), and same-day access to template fixes is worth more than reproducibility at
this stage. Revisit once the templates repo starts cutting real releases. Do not "fix" this
to a tag without checking that the tag actually contains every included file.

`docker-sign.yml` is **deprecated** — signing already happens inside `docker-build.yml`.
Do not include it.

**GitLab is the only platform a repo is required to support.** Images, charts and packages
all live in the GitLab registries of the owning group; no repo needs a GitHub account, a
GHCR path or a GitHub Actions workflow to be complete.

**GitHub is optional.** A repo that is *also* published to GitHub (the upstream standard
template is) mirrors the same gates through
[`korkin25/open-ci-actions@v1`](https://github.com/korkin25/open-ci-actions)
(`detect` → `python` / `sast` / `docker` / `helm` / `functional`). Keep the two in parity or
drop the GitHub half entirely — a half-maintained second pipeline is worse than none.

**Gate policy:** a newly-added scanner starts in report mode (soft-fail); tighten it to a
hard gate once the baseline is clean — but **never silently drop one**.

## Runtime contract

Every service must satisfy these, because CI, the chart and the platform's tier-(d) tests all
depend on them:

- **`GET /health` returns 200** with a JSON body carrying at least `{"status", "version"}`.
  A service with no HTTP surface still exposes it, or supplies an exec probe that proves
  liveness — the chart renders one or the other, never neither.
- **Config comes from the environment**, never from a file baked into the image. Every
  variable is documented in `docs/configuration.md`. In the cluster it arrives via a
  namespace-wide ConfigMap plus a per-service Secret; locally via the dev stack.
- **Runs as non-root** on a read-only root filesystem. `deploy/Dockerfile` creates a
  dedicated uid/gid; the chart sets `runAsNonRoot`, `readOnlyRootFilesystem`,
  `allowPrivilegeEscalation: false`, drops all capabilities, and mounts an `emptyDir` at
  `/tmp` for anything that must write.
- **Logs go to stdout**, structured, with no secrets in them.
- **Shutdown is graceful**: SIGTERM stops intake, finishes in-flight work, commits offsets,
  exits non-zero only on real failure.
- **Message handling is idempotent and commits after success**, never before. Auto-commit on
  receipt silently loses messages on a crash.

## Chart contract

- `Chart.yaml` `version`/`appVersion` are **placeholders**; CI overwrites both with
  `GitVersion_SemVer`. Never hand-edit them.
- `values.yaml` `image.repository` and `image.tag` are likewise CI-written. A human-set image
  tag in a chart is always a bug.
- The chart carries **defaults only**. Per-environment values live in the platform repo,
  never here — this chart must render for any environment.
- The chart never templates a secret value. Secrets arrive by reference to an existing
  Secret.
- Resource requests and limits are set. `resources: {}` is not acceptable for a service that
  runs in a shared cluster.

## Release

1. Merge to `dev` → a `-dev` build. Merge to `rc` → a pre-release. Merge to `release` →
   the stable version. Each is approval-gated.
2. CI publishes the image and the chart at the same SemVer and commits `.versions/*.env`.
3. **Deployment is a separate, explicit act in the platform repo**: bump `chartVersion` in
   the target environment's `bundle.yaml`. That MR is the deployment, and reverting it is
   the rollback.

A service repo pipeline never touches a cluster, and never runs `kubectl apply`.

## Published artifacts

- Image → `registry.gitlab.com/@@GROUP@@/@@PROJECT@@`
- Chart (OCI) → `oci://registry.gitlab.com/job-agent/charts/@@PROJECT@@`

Both tagged with the same `GitVersion_SemVer`. Both in GitLab — there is no second registry
to keep in sync.
