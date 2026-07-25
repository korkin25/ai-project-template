# app Helm chart

Generic application chart for the ai-project-template. Deploys the container image published
to GHCR by CI, and is itself packaged and pushed as an OCI chart to
`ghcr.io/<owner>/charts/<name>`.

A single **Deployment** runs the container (default command `app-serve`) on port 8080,
fronted by a ClusterIP Service, with `GET /health` probes.

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

## Secrets

The chart never templates secret values. Provide runtime secrets via an existing Secret and
enable `envFrom.secret`. See [../docs/configuration.md](../docs/configuration.md) for the
full env-var list.

## Values of note

| Key | Default | Purpose |
|-----|---------|---------|
| `image.repository` / `image.tag` | `ghcr.io/OWNER/REPO` / appVersion | image |
| `command` | `["app-serve"]` | container entry point |
| `persistence.enabled` | `false` | data PVC (sample is stateless) |
| `envFrom.secret.enabled` | `false` | inject an existing Secret |
| `gatewayApi.enabled` | `false` | external access via a Gateway API HTTPRoute |
| `serviceMonitor.enabled` | `false` | Prometheus Operator scrape |
