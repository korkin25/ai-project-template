
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

On **GitLab**, `.gitlab-ci.yml` includes these from the group's shared CI-templates repo. On
**GitHub** the equivalents are reusable workflows; the job set and its guarantees are the
same, and the table below is the contract either way.

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

**Prefer a tag. Tracking a branch is allowed, but only as a recorded decision** — written in
`docs/architecture.md` with its blast radius stated plainly — never as something nobody got
around to. It is a defensible trade-off when the templates repo cuts no releases and same-day
access to fixes is worth more than reproducibility; it is indefensible when it happened by
accident. Before switching an existing repo to a tag, check the tag actually contains every
included file: a tag that trails the branch by a long way is worse than the branch.

`docker-sign.yml` is **deprecated** — signing already happens inside `docker-build.yml`.
Do not include it.

### Choosing a host

**This standard is host-agnostic.** The gates, the artifacts and the release model are the
same on GitLab and on GitHub; only the wiring differs. **A project picks one host, once, and
records the choice in its own `docs/architecture.md`** — that is a project decision, never
the standard's.

| | GitLab | GitHub |
|---|---|---|
| Pipeline | `.gitlab-ci.yml`, composed from `include:` of a shared templates repo | `.github/workflows/ci.yml`, composed from `uses:` of a reusable-workflow repo |
| Job set | `globals` · `auto-semversioning` · `lint` · `sast` · `docker-build` · `helm-package` · `functional` · `commit_changes` | `detect` → `python` / `sast` / `docker` / `helm` / `functional` |
| Images | the group's container registry | the org's container registry |
| Charts (OCI) | the same registry, under a charts path | the same registry, under a charts path |
| Packages | the group's package registry | the language's public index, or the org's |
| Review unit | merge request | pull request |
| Ownership | `CODEOWNERS` + approval rules | `CODEOWNERS` + required reviewers |
| Dependency bot | Renovate | Dependabot or Renovate |
| Templates | `.gitlab/merge_request_templates/` | `.github/PULL_REQUEST_TEMPLATE.md` |

**Support exactly one.** Publishing to both is allowed only when someone owns keeping them in
parity: a half-maintained second pipeline is worse than none, because it fails for reasons
nobody investigates and trains everyone to ignore a red check. If the second host exists only
to mirror the source, give it no pipeline at all rather than a decorative one.

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
- **Exposes `GET /metrics`** in Prometheus text format, and the chart ships a `ServiceMonitor`
  (or the equivalent scrape config) that is enabled wherever a metrics backend exists. A chart
  that templates a `ServiceMonitor` against an endpoint the service does not serve is a
  scrape target that fails silently — the panels stay empty and nobody is told why.
- **Logs go to stdout**, one JSON object per line, using the shared library's schema so field
  names are identical across services. No secrets, no personal data. Every value that anyone
  would filter by is its own field, never interpolated into the message text — see
  *Observability*.
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

- Image → `<registry>/@@GROUP@@/@@PROJECT@@`
- Chart (OCI) → `oci://<registry>/<group>/charts/@@PROJECT@@`

Both tagged with the same `GitVersion_SemVer`, and both in the **same registry** — the one
the hosting platform already provides. A second registry is a second set of credentials, a
second retention policy and a second thing to be out of sync; adopt one only for a reason
that survives being written down.

The concrete paths are the consuming group's to choose and belong in its own
`docs/architecture.md`, not here.
