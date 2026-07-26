# Architecture — @@PROJECT@@

> **Design-before-code lives here.** No change is made until the design is written down: what
> it changes, what depends on it, how it is verified, and how it is undone. On
> infrastructure, "how it is undone" is the part that must exist *before* the change, not
> after — a bad CNI change costs the cluster and a bad runner change costs CI itself.

## What this repo owns

The **substrate everything else assumes**. It contains no application code, builds no image
and publishes no package. Its output is *applied configuration*: a cluster that exists, a
runner that is registered, an operator that is installed.

- Cluster bootstrap: the distribution, the CNI, the storage class, the Gateway.
- Cluster-wide platform components: cert-manager, the secrets operator, the secret store,
  reload controllers, monitoring CRDs.
- CI runners, and the credentials they need in order to exist at all.
- The GitOps controller itself, and its sync root.

## What this repo does NOT own

- **Which version of which application runs.** That is the platform repo's `bundle.yaml`.
- **Any application chart or manifest.**

Both directions are worth stating, because "install the operator" and "deploy the app that
needs the operator" look almost identical and end up duplicated otherwise:

> **This repo installs the *capability*; the platform repo decides *what uses it, and at
> which version*.**

An infra repo that pins an application version has taken over a job it cannot do
consistently — it would have to know which application versions are compatible with each
other in each environment, which is precisely what the platform repo exists to know.

## Layout

```
ansible.cfg                     committed defaults, so "worked on my machine" cannot happen
playbooks/                      entry points; site.yml provisions the substrate
roles/                          locally authored roles (third-party roles are pinned, not vendored)
roles/requirements.yml          third-party roles, exact versions
collections/requirements.yml    Ansible collections, exact versions
inventories/<env>/              one directory per environment — hosts.yml + group_vars/
manifests/                      raw cluster prerequisites (namespaces, RBAC, storage classes)
docs/runbook.md                 how to recover each component — the real test of this repo
```

## Non-negotiables

These are not aspirations; every change is reviewed against them.

- **Idempotent.** Running it twice changes nothing the second time. Every run is a
  reconciliation, never a one-shot script whose effect depends on prior state.
- **Reproducible from zero.** The repo must be able to build the substrate on a fresh
  machine. A step that only works because of undocumented existing state is a defect —
  write it down or automate it.
- **Nothing applied by hand.** A change made with `kubectl edit` and not committed here is
  either silently reverted by the reconciler or silently survives and diverges. If it
  matters, it is in git.
- **Pinned versions.** Every chart, operator, image and collection is referenced by an exact
  version. `latest` in an infra repo is an outage waiting for a quiet week.
- **Credentials from the environment**, never from a committed file. The bootstrap procedure
  in [configuration.md](configuration.md) names where each value comes from.

## CI boundary

CI **lints and validates only — it never applies**. A pipeline that can apply must hold
cluster-admin credentials, which makes every job in it (including a third-party linter) a
path to the cluster; that standing risk is larger than the manual step it saves. The
`.gitlab-ci.yml` header states this at length so it is not quietly relaxed later.

Applying is a human step, planned first (`--check --diff`, `helm template`, `flux diff`) and
approved every time. The procedures are in [runbook.md](runbook.md).

## Verification model

There are no meaningful unit tests here; verification is the **state of the system**. Every
change is verified by reading the state back — the node is `Ready`, the operator is
`Running`, the runner reports `online`, the reconciler shows no drift — and that read-back is
recorded verbatim in `AUTOPILOT-LOG.md` under **Verified by**.

## Decisions log

Architectural decisions as `@@PREFIX@@-D<n>`: context → options → decision → consequences.
Include the rollback in the consequences — on infrastructure it is part of the decision, not
a detail.

- _@@PREFIX@@-D1 — … (replace: e.g. the choice of Kubernetes distribution, or of secret
  store, with what it costs to reverse)._
