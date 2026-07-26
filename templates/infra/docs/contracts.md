# Contracts — @@PROJECT@@

An infra repo publishes no package and no API, but it very much has contracts: **the
capabilities other repos assume exist**. They are invisible precisely because they work, so
they are written down here — a capability nobody documented is one that gets removed during a
cleanup, breaking repos that never mentioned needing it.

## Provided by this repo

Anything listed here may be depended on. Removing or renaming one is a **breaking change**
for every repo in the group, which makes it an architectural decision requiring approval —
and it needs a ticket in each affected repo before the change lands, not after.

| Capability | Shape / name | Consumed by | Notes |
|---|---|---|---|
| CI runner | tag `@@RUNNER_TAG@@` | every repo's `.gitlab-ci.yml` (`.default_runner`, `.default_runner_infra`, and the untagged jobs each repo overrides by name) | Renaming the tag strands every pipeline in `pending` — with no error, because a job waiting for a tag nobody offers is indistinguishable from a busy runner. |
| Namespaces | `platform`, `platform-system` | platform repo bundles; every service chart | PSA labels are enforced at admission — a workload that is not `restricted`-compatible will be rejected in `platform`. |
| Registry pull secret | `gitlab-registry` (in each application namespace **and** in the Flux namespace) | every chart's `imagePullSecrets`; Flux OCIRepository | Must exist in both places or charts fail to pull with an error that names neither. |
| Gateway | the cluster Gateway resource | every service chart's `httpRoute.parentRefs` | Services attach to it by reference; the Gateway itself is never templated by a service chart. |
| StorageClass | the cluster default | anything with a PVC | Changing the default silently changes where new volumes land. |
| Secrets operator + store | `ExternalSecret` / `ClusterSecretStore` | every service that needs a secret | Path prefixes are per environment, so a dev environment structurally cannot read production keys. |
| GitOps controller | Flux, and its sync root | the platform repo | The platform repo's bundles are reconciled from here. |

## Consumed by this repo

Each of these is code from someone else that ends up running in the cluster, so each is pinned
to an exact version and each pin is somewhere `scripts/check-versions.py` can read it.

| Contract | Owner | Pinned at | Used for |
|---|---|---|---|
| Chart sources | upstream vendors | `repositories/` — `HelmRepository` / `OCIRepository`, one place to audit where code enters the cluster from | cert-manager, secrets operator, Gateway API, the runner |
| Component versions | upstream vendors | the `version` / `ref.tag` in each release under `apps/<component>/`, exact — never a range | what the reconciler actually installs |
| Container images | upstream vendors | exact tags (a digest wherever the vendor publishes one) in `apps/<component>/app/` | the pods that make up each component |
| GitOps controller API | upstream | the `apiVersion` of every `Kustomization`, `HelmRelease` and source object | a controller upgrade that drops an API version stops reconciliation silently, so this is a version to read release notes for |
| Kubernetes API | the distribution, chosen in the machine layer | the `apiVersion` of everything in `manifests/`, validated by `kubeconform -strict` in CI | the cluster prerequisites |
| Shared CI templates | `@@CI_TEMPLATES_PROJECT@@` | `ref:` in `.gitlab-ci.yml` | the lint/validate pipeline |

## Changing a capability

1. **Find out who depends on it** before anything else — the table above is the starting
   point, `grep` across the group is the check.
2. **Additive first.** Create the new namespace/secret/tag alongside the old one; do not
   rename in place. A rename in infrastructure is a simultaneous outage in every consumer.
3. **Move the consumers**, one MR per repo, each citing the platform id, each verified by its
   own pipeline.
4. **Only then remove the old capability**, and record the removal in `CHANGELOG.md` — this
   is the one repo whose changelog other teams need to read.
5. Update this table in the same change as the manifest, the `ks.yml` or the release that
   provides the capability. A table updated afterwards is wrong for exactly as long as it
   takes someone to notice — and the person who notices is a consumer whose deploy just broke.
