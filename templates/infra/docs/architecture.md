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

## Where this repo starts

**The machine layer is outside the GitOps tree.** How the nodes come to exist and how the
Kubernetes distribution is installed is a procedure in [runbook.md](runbook.md), and it may
use whatever tool suits the environment. This repo takes over at the first thing that can be
reconciled: the GitOps controller and its sync root.

The boundary is deliberate, and it is drawn where the *mechanism* changes rather than where
the responsibility does. Everything after it is declarative, diffable and self-healing;
everything before it happens once per machine and stays done. A tree that mixes the two
produces a repo where half the state drifts silently and the other half cannot — and no way
to tell, for any given file, which half it is in.

## Layout

```
clusters/<cluster>/             the sync root: which components THIS cluster runs
apps/<component>/ks.yml         the reconciler's entry — path, interval, dependencies, health
apps/<component>/app/           its manifests, or a release plus values
repositories/                   pinned chart and image sources, by exact version
manifests/                      raw cluster prerequisites (namespaces, RBAC, storage classes)
scripts/check-versions.py       what is pinned vs what is newest — input to the periodic audit
docs/runbook.md                 how to recover each component, and the machine-layer bootstrap
```

The split between `clusters/` and `apps/` is the one structural decision worth defending.
`apps/<component>/` answers *how* a component is deployed, once, for every cluster; the sync
root answers *which* components this particular cluster runs. Adding a component to one
cluster is then a one-line change to that cluster's kustomization, not a copied directory —
and the copy is what would eventually drift, silently, in the cluster nobody looks at.

The corollary is that a sync root which pulls in the whole catalogue defeats the split. It is
how a laptop environment ends up scheduling a production stack, and the failure is only
visible as memory pressure hours later.

Versions live in `repositories/` and in each release, never in the sync root. A cluster
chooses *what* it runs; it does not get to choose *which version*, because two clusters on
two versions of the same operator is precisely the state this repo exists to prevent.

## Non-negotiables

These are not aspirations; every change is reviewed against them.

- **Idempotent.** Reconciling twice changes nothing the second time. The controller re-applies
  continuously by design, so a component whose apply is not idempotent is not merely untidy —
  it churns the cluster on a timer.
- **Reproducible from zero.** The repo must be able to build the substrate on a fresh
  machine. A step that only works because of undocumented existing state is a defect —
  write it down or automate it.
- **Nothing applied by hand.** A change made with `kubectl edit` and not committed here is
  either silently reverted by the reconciler or silently survives and diverges. If it
  matters, it is in git.
- **Pinned versions.** Every chart, operator and image is referenced by an exact version in
  `repositories/` or in the release that consumes it. `latest` in an infra repo is an outage
  waiting for a quiet week — and under a reconciler it is worse, because the upgrade happens
  on the controller's schedule rather than on a human's.
- **Credentials from the environment**, never from a committed file. The bootstrap procedure
  in [configuration.md](configuration.md) names where each value comes from.

## CI boundary

CI **lints and validates only — it never applies**. A pipeline that can apply must hold
cluster-admin credentials, which makes every job in it (including a third-party linter) a
path to the cluster; that standing risk is larger than the manual step it saves. The
`.gitlab-ci.yml` header states this at length so it is not quietly relaxed later.

**There is no local apply step either.** The human act is reading the plan and merging;
merging is the apply, and the reconciler does the rest. What a human runs beforehand is
`flux build kustomization <name> --path clusters/<cluster>` to see what would be rendered,
`flux diff` and `kubectl diff -f manifests/` to see what would change. The procedures are in
[runbook.md](runbook.md).

The exceptions are the bootstrap steps that necessarily precede the controller — there is
nothing to reconcile from yet — and they are hand-run, approved individually, and listed in
[configuration.md](configuration.md). Every one of them is a step this repo works to keep
short, because it is state that no diff can show you.

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
