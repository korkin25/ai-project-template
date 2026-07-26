
---

# Profile: platform

The **platform** repo is the integration truth. It answers one question no service repo can:
*what is actually running, where, at which version.* It holds no application code, builds no
image, and publishes no package. Its released artifact is **the state of an environment**, and
a release is a merge.

## What it owns

- The **bundle** for each environment — the declarative list of what is deployed and at which
  version.
- **Per-environment values** for every chart.
- The **system-wide architecture**: how the services fit together, the contract registry, the
  cross-repo decision log.
- **Tier-(d) cross-service end-to-end tests**.

## What it does NOT own

- Cluster bootstrap, the CNI, the ingress/gateway, cert-manager, the secrets operator, Vault —
  those belong to an `infra` repo that owns the cluster itself. **The platform repo assumes a
  working cluster and consumes it.** If a platform component is missing, that is a ticket in
  the infra repo, not a manifest here.
- Any service's chart. A chart ships from the service that it deploys.

Draw this boundary explicitly in `docs/architecture.md`, naming the infra repo, because it is
the single most common source of duplicated and conflicting manifests.

## Layout

```
clusters/<cluster>/environments/<env>/
  bundle.yaml            THE descriptor — what runs here, at which version
  values/
    common.yaml          defaults applied to every chart in this environment
    <service>.yaml       per-service overrides
  manifests/             raw resources that are not a service chart (DB clusters, topics,
                         ExternalSecrets), one directory per component
bundle.schema.json       JSON Schema, additionalProperties: false
scripts/
  validate-bundles.py    schema gate
  render.py              bundle.yaml -> Flux OCIRepository + HelmRelease
e2e/                     tier-(d) tests
docs/                    architecture.md, contracts.md, environments.md, tests.md
```

**Environments are directories, not branches.** One cluster, one Flux instance, and the whole
state diffable in a single tree. A second cluster is a sibling directory. (Branch-per-cluster
exists elsewhere to serve two independent GitOps controllers; adopting it without that
constraint just hides the diff.)

## The bundle

`bundle.yaml` is the only file that carries a version, and the only file a release touches.

```yaml
name: job-agent-dev            # prefix for generated resource names
namespace: job-agent           # the Kubernetes namespace; also the URL segment
publish_domain: dev.example    # base domain for exposed services
imageRegistry: registry.gitlab.com/job-agent
vaultPathPrefix: dev           # ExternalSecret keys resolve under this
microservices:
  - service: processing
    repoURL: oci://registry.gitlab.com/job-agent/charts
    chartVersion: 0.1.3        # EXPLICIT. never a range.
platform:
  - component: redpanda
    repoURL: oci://.../redpanda
    chartVersion: 5.9.2
```

Rules that make it safe to automate:

- **`additionalProperties: false` everywhere** in the schema, so a typo fails CI instead of
  silently doing nothing.
- **`chartVersion` is an exact version.** Never `>=`, never `~`, never `latest`. A range means
  nobody can state what is running and a rollback stops being a revert.
- **One string, three roles**: `service` is simultaneously the chart name, the values filename
  and the generated resource name. Never let them diverge.
- **Comment the non-obvious.** Any tuned value carries an inline comment saying why, with the
  ticket id. A number nobody can explain is a number nobody dares change.

## Deployment and promotion

- A service publishes; the platform **pins**. Read the service's committed
  `.versions/helm-chart.env`, set that `chartVersion` in the target environment's bundle,
  open an MR. **That MR is the deployment.**
- **Promotion is a copy of a version between environment directories**, in an MR, after
  tier-(d) is green in the source environment. Never a rebuild, never a retag.
- **Rollback is `git revert`.** If a rollback ever requires anything else, the model has been
  broken somewhere — fix that, do not work around it.
- **Bumping a version here always requires human approval.** It is a deployment, not an edit.

## Secrets

No secret value is ever committed. Secrets are declared by *reference* and resolved in-cluster
by the External Secrets Operator against a `ClusterSecretStore`:

- **Pull from the store** for anything a human or another system provisions (registry
  credentials, API keys).
- **Generate in-cluster** for anything with no external source (service-to-service tokens,
  database passwords), then push it to the store so both sides can read the same value.
- Key naming follows `{vaultPathPrefix}/{path}` from the bundle, so an environment's secrets
  are namespaced by construction and a dev bundle cannot read production keys.

## CI

The pipeline validates; it never deploys — Flux reconciles from git, so CI having cluster
credentials would defeat the pull model.

| Job | Checks |
|---|---|
| `yamllint` | formatting across the tree |
| `validate-bundles` | every `bundle.yaml` against `bundle.schema.json` |
| `render-diff` | `render.py` produces valid Flux resources; the diff is shown in the MR |
| `e2e` | tier-(d), against a real cluster (see below) |

## Tier-(d) end-to-end

These prove the services work *together*, which no service repo can do alone.

- They run against a **real cluster**, not a mock. A local k3s is a legitimate target and is
  the default for development.
- Each test names the contract it exercises, so a failure points at an owner rather than at
  "the system".
- A contract change in any service repo updates the matching tier-(d) test **here**, in the
  same change set, linked by the platform id.
- E2E is a **promotion gate**: green in the source environment before a version moves onward.

## Cross-repo coordination

The platform repo is where multi-repo work is planned and tracked:

- **Platform ids** (`@@PREFIX@@-<n>`) name work that spans repos; each participating repo
  opens its own local ticket referencing it.
- **`@@PREFIX@@-D<n>`** records decisions that no single service repo can own: topology,
  contract changes, environment shape, shared dependencies.
- `docs/contracts.md` is the **registry**: every contract, its owning repo, and its consumers.
  When a service repo asks "who consumes this topic", this file is the answer — keep it
  accurate or the *Cross-repo contracts* protocol has nothing to stand on.
