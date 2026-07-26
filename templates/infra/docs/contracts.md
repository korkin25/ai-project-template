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
| CI runner | tag `job-agent-local` | every repo's `.gitlab-ci.yml` (`.default_runner`, `.default_runner_infra`, and the untagged jobs each repo overrides by name) | Renaming the tag strands every pipeline in `pending`. |
| Namespaces | `platform`, `platform-system` | platform repo bundles; every service chart | PSA labels are enforced at admission — a workload that is not `restricted`-compatible will be rejected in `platform`. |
| Registry pull secret | `gitlab-registry` (in each application namespace **and** in the Flux namespace) | every chart's `imagePullSecrets`; Flux OCIRepository | Must exist in both places or charts fail to pull with an error that names neither. |
| Gateway | the cluster Gateway resource | every service chart's `httpRoute.parentRefs` | Services attach to it by reference; the Gateway itself is never templated by a service chart. |
| StorageClass | the cluster default | anything with a PVC | Changing the default silently changes where new volumes land. |
| Secrets operator + store | `ExternalSecret` / `ClusterSecretStore` | every service that needs a secret | Path prefixes are per environment, so a dev environment structurally cannot read production keys. |
| GitOps controller | Flux, and its sync root | the platform repo | The platform repo's bundles are reconciled from here. |

## Consumed by this repo

| Contract | Owner | Pinned at | Used for |
|---|---|---|---|
| Ansible collections | upstream Galaxy | `collections/requirements.yml`, exact versions | provisioning modules |
| Ansible roles | upstream | `roles/requirements.yml`, exact versions | provisioning |
| Component charts | upstream | `inventories/<env>/group_vars/all.yml`, exact versions | cert-manager, secrets operator, Gateway API |
| Shared CI templates | `open_ci_cd/templates` | `ref:` tag in `.gitlab-ci.yml` | the lint/validate pipeline |

## Changing a capability

1. **Find out who depends on it** before anything else — the table above is the starting
   point, `grep` across the group is the check.
2. **Additive first.** Create the new namespace/secret/tag alongside the old one; do not
   rename in place. A rename in infrastructure is a simultaneous outage in every consumer.
3. **Move the consumers**, one MR per repo, each citing the platform id, each verified by its
   own pipeline.
4. **Only then remove the old capability**, and record the removal in `CHANGELOG.md` — this
   is the one repo whose changelog other teams need to read.
5. Update this table in the same change as the manifest or playbook.
