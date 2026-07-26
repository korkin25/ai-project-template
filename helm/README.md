# app Helm chart

Generic application chart for the ai-project-template. Deploys the container image published
to GHCR by CI, and is itself packaged and pushed as an OCI chart to
`ghcr.io/<owner>/charts/<name>`.

A single **Deployment** runs the container (default command `app-serve`) on port 8080,
fronted by a ClusterIP Service, with startup/readiness/liveness probes on `GET /health` and
an optional ServiceMonitor scraping `GET /metrics` — both paths the sample app really serves.

## Install

```bash
helm install app oci://ghcr.io/<owner>/charts/app --version 0.1.0 \
  --set image.repository=ghcr.io/<owner>/<repo>
```

## Adopt

- Rename the chart (`Chart.yaml: name`) and the `app.*` helper prefix in `templates/_helpers.tpl`.
- Point `image.repository` at your GHCR image (CI publishes `ghcr.io/<owner>/<repo>`).
- Enable what you need: `persistence` (a data PVC), `gatewayApi` (an HTTPRoute — set
  `parentRefs` to your Gateway), `serviceMonitor`, `autoscaling`, `podDisruptionBudget`. For
  advanced volumes use `extraVolumes` / `extraVolumeMounts`.

## Configuration and secrets

Non-secret values go in `env` (rendered into a chart-owned ConfigMap, with a `checksum/env`
pod annotation so a change actually rolls the pods). Namespace-wide platform configuration is
referenced by name in `envFrom.configMaps`, and this service's secret via `envFrom.secret` —
the chart never templates a secret **value**. See
[../docs/configuration.md](../docs/configuration.md) for the full env-var list.

## Hardening

`runAsNonRoot`, `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`,
`capabilities.drop: [ALL]` and `seccompProfile: RuntimeDefault` are fixed in
`templates/deployment.yaml` and are **not** values — one line in one environment's values
must not be able to weaken them. Only `runtimeUser.uid`/`gid`/`fsGroup` are configurable,
because those are a fact about the image you build.

## Values of note

| Key | Default | Purpose |
|-----|---------|---------|
| `image.repository` / `image.tag` | `ghcr.io/OWNER/REPO` / appVersion | image (CI-written) |
| `command` | `["app-serve"]` | container entry point |
| `runtimeUser.uid` / `.gid` / `.fsGroup` | `10000` | must match `deploy/Dockerfile` |
| `resources` | 50m/128Mi → 500m/512Mi | requests **and** limits; measure and adjust |
| `terminationGracePeriodSeconds` | `30` | SIGTERM budget for graceful shutdown |
| `envFrom.configMaps` | `[]` | existing ConfigMaps by name (`optional: true`) |
| `envFrom.secret.enabled` | `false` | inject an existing Secret |
| `persistence.enabled` | `false` | data PVC (sample is stateless) |
| `gatewayApi.enabled` | `false` | external access via a Gateway API HTTPRoute — requires `gatewayApi.parentRefs`, else rendering fails |
| `serviceMonitor.enabled` | `false` | Prometheus Operator scrape of `serviceMonitor.path` |
| `autoscaling.enabled` | `false` | HPA; when on, `replicaCount` is no longer authoritative |
| `podDisruptionBudget.enabled` | `false` | enable for anything above one replica |
