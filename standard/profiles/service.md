
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

**One host, or a mirror. Never two repositories.** The distinction is what makes the
difference, and it is about who guarantees parity:

- **Two hand-maintained repositories** is the bad case. They drift, because nothing forces
  them not to. A half-maintained second pipeline is worse than none: it fails for reasons
  nobody investigates and trains everyone to ignore a red check.
- **One repository mirrored to a second host** is legitimate and sometimes better. Parity is
  mechanical — the mirror cannot hold a file the source does not — so the two pipelines run
  the *same committed inputs* and any difference in outcome is a difference in the hosts, not
  in the code.

**A mirror should run the full gate set, not a decorative subset.** That is the entire value:
running both is how host-specific defects surface. Concretely, in this standard's own repo,
a smoke test that had passed on one host for months could never have passed on the other —
the probe assumed a network layout that host does not have. Nothing but running it there
would have found it, and every repo scaffolded from here had inherited the same script.

**The rule that follows, for a mirrored repo: every change must be universal.** No patch may
assume one host. In practice that means the governance artifacts exist in both dialects and
are edited together — `CODEOWNERS` in each syntax, both dependency bots, both merge/pull
templates, both pipelines — and a change touching one side without the other is incomplete
work, not a follow-up. Where a capability genuinely exists on only one host, the difference
is written down in `docs/architecture.md` rather than left for a reader to discover from a
red pipeline.

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

The chart is the only thing standing between the image and the cluster, and it is reviewed by
people who will never open the templates. Every rule below is one a reviewer can check by
reading `values.yaml` and running `helm template`.

### Version and image

- `Chart.yaml` `version`/`appVersion` are **placeholders**; CI overwrites both with
  `GitVersion_SemVer`. Never hand-edit them — but keep them valid SemVer, or the chart stops
  rendering locally.
- `values.yaml` `image.repository` and `image.tag` are likewise CI-written. A human-set image
  tag in a chart is always a bug: it decouples the chart version from the code it deploys,
  and nothing fails until the wrong build ships.
- The chart passes `.Chart.AppVersion` into the container (`APP_VERSION` or equivalent),
  because **the image cannot know its own tag**. `/health` and `/metrics` must report the
  released version, not a constant frozen at build time. Set it as a container `env` entry so
  nothing in `envFrom` can shadow it.
- `helm.sh/chart` and `app.kubernetes.io/version` carry that version into metadata, so
  `kubectl get deploy --show-labels` answers "what is running here?" without the platform
  repo. **Selector labels are a strict subset and never carry a version**: a Deployment's
  selector is immutable, so a version there makes every upgrade fail with "field is
  immutable" and forces a delete/recreate — an outage per release.

### Scope — what may and may not be in the chart

- **Defaults only.** Per-environment values live in the platform repo, never here. This chart
  must render for *any* environment, so nothing in `values.yaml` names a cluster, a domain, a
  namespace or an environment.
- **Never a secret value.** Secrets arrive by reference to a Secret that already exists in the
  namespace. A rendered secret lands in the release manifest, in cluster state, and in every
  `helm get values` output.
- **No coupling to a GitOps controller or a secrets operator.** What applies the release is
  the platform repo's business, not the chart's.
- **No NetworkPolicy.** Namespace traffic policy is the infra repo's; a per-service policy
  fighting the cluster default is how a service loses its egress on a Friday.

### Configuration

- Env arrives via `envFrom`: the namespace-wide ConfigMap the platform provides, plus this
  service's own Secret, **both referenced by name**. The shared ConfigMap is `optional: true`
  — one that has not been created in this namespace yet otherwise wedges the pod in
  `CreateContainerConfigError`, which names no cause.
- Values the chart itself owns may render inline in the pod spec or into a chart-owned
  ConfigMap. **A chart-owned ConfigMap requires a `checksum/…` pod annotation over it.**
  Without one, a values change rewrites the ConfigMap and no pod ever re-reads it: the release
  reports success while the old configuration keeps running. Inline env needs no checksum — it
  is already part of the pod template, so changing it rolls the pods by itself.
- Every variable the chart sets appears in `docs/configuration.md`.

### Hardening — fixed in the template, not a values knob

The *Runtime contract* says what must be true of the container. The chart's obligation is that
**none of it is overridable**: `runAsNonRoot`, `readOnlyRootFilesystem`,
`allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]` and
`seccompProfile: RuntimeDefault`, at pod *and* container level, written into the template.
Exposed as values, one line in one environment's bundle weakens the whole set, in a repo where
nobody reviews security posture. A workload that genuinely cannot comply is a decision
recorded in `docs/architecture.md`, not an override.

Only uid/gid/fsGroup are values, because they are a fact about the image and must match
`deploy/Dockerfile`. `drop: [ALL]`, never a list of named capabilities — so a capability added
to a future default set is dropped too.

`automountServiceAccountToken: false` unless the service really calls the Kubernetes API; the
mounted token is otherwise just a credential waiting to be found.

### Probes

- **All three are rendered.** `startupProbe` guards the boot, `readinessProbe` removes an
  endpoint, `livenessProbe` kills a container. Without a startup probe the only way to survive
  a slow boot is a long liveness `initialDelaySeconds`, which then delays detection of a real
  hang for the rest of the pod's life.
- Readiness reacts fast, liveness slowly. The costs are not symmetric: one withdraws traffic,
  the other destroys a process mid-work.
- A service with no HTTP surface renders **exec** probes instead — one or the other, never
  neither. A Deployment with no probe reports Ready the moment the process starts, so a
  rollout of a broken build completes green.
- `terminationGracePeriodSeconds` is at least the shutdown budget the process needs. Shorter,
  and the graceful shutdown the runtime contract promises is a fiction the pod never finishes.

### Resources and disruption

- Requests **and** limits are set. `resources: {}` is not acceptable for a service on a shared
  cluster: with no request the scheduler treats the pod as free and packs nodes until
  something is OOM-killed; with no limit one leaking pod evicts its neighbours. The numbers
  are a starting point to be measured, not a permanent guess.
- A `PodDisruptionBudget` is templated, and enabled for anything above one replica — a node
  drain otherwise takes every replica at once, a voluntary outage nobody chose. A budget that
  leaves no room (`minAvailable` ≥ `replicaCount`) is the opposite failure: drains and cluster
  upgrades hang forever with nothing red on the release. Reject it at render time.
- If the chart templates an `HorizontalPodAutoscaler`, `replicaCount` stops being the source
  of truth; a chart that keeps asserting both fights itself on every reconcile.

### Networking

- External access is a Gateway API **`HTTPRoute`, never an `Ingress`.** Ingress is
  feature-frozen upstream and every non-trivial behaviour lives in controller-specific
  annotations, which makes the manifest unportable and unreviewable.
- **Off by default.** Most services expose nothing, and a worker reachable from the internet
  by accident is an incident — defaults are what people forget to change.
- `parentRefs` has **no default**, and rendering **fails loudly** when the route is enabled
  without one, or without a Service to send traffic to. An HTTPRoute with no parent is
  accepted by the API server and then routes nothing: `Accepted=False`, no event on the
  Deployment, no error anywhere a human is looking.
- The Service is `ClusterIP`. A per-service LoadBalancer or NodePort bypasses the gateway's
  TLS, auth and rate limiting, and is invisible in the routing config someone reads when
  asking "what is exposed?".
- Ports are targeted **by name**, so the container port can move without an edit in every
  consumer of the Service.

### Identity and registry

- The chart creates **its own ServiceAccount** (name overridable). Sharing the namespace
  `default` account means the first RBAC role or cloud workload identity bound to it is
  silently granted to every pod in the namespace.
- `imagePullSecrets` are referenced **by name only** — the Secret is the infra repo's to
  provision, and a chart that templates one has templated a credential.

### Observability

- The chart ships a `ServiceMonitor` (or the equivalent scrape config), enabled wherever a
  metrics backend exists — see *Observability*.
- **The scrape path must be one the service actually serves, and the port is the Service
  port's name, not a number.** A `ServiceMonitor` aimed at an endpoint that 404s is a scrape
  target that fails silently: the panels stay empty and nobody is told why. The `/metrics`
  handler and the `ServiceMonitor` land in the **same change**; neither is allowed to exist
  alone.

### CRD-backed resources

`HTTPRoute` and `ServiceMonitor` need CRDs that `helm lint` cannot see. Off means absent, not
degraded — but turning one on adds a cluster prerequisite, and a release templating a kind
whose CRD is missing fails at **apply** time, not at lint time. The prerequisite is declared
in the platform's `requirements.yaml` like any other capability; the chart only reads the flag.

### Gate

CI runs `helm lint` and `helm template` on every ref, and renders the chart **with the
optional features on**, not only with defaults — a template exercised only by its defaults is
untested for every environment that turns something on. `fail` guards are how a
misconfiguration becomes a red pipeline instead of a resource that exists and does nothing.

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
