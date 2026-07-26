# @@PROJECT@@

@@DESCRIPTION@@

The **substrate** everything else in the platform assumes: the cluster's own components and
the capabilities other repos declare they need. It follows the **infra** profile of the shared
standard (`standard/profiles/infra.md`). It contains no application code, builds no image and
publishes no package — its output is *applied configuration*.

| | |
|---|---|
| Shape | A GitOps tree reconciled from git — `clusters/`, `apps/`, `repositories/` |
| Cluster prerequisites | `manifests/` — namespaces, cluster-scoped objects |
| Recovery procedures | [`docs/runbook.md`](docs/runbook.md) — the real test of this repo |
| Rules | [`CLAUDE.md`](CLAUDE.md) — generated from `standard/` |

> **CI lints and validates. It never applies.** The reconciler applies, from git. A pipeline
> holding cluster-admin credentials is a worse risk than the manual step it saves, and it
> would defeat the pull model this repo exists to serve.

## Scope — where this repo starts

**Machine-level bootstrap is out of scope of the GitOps tree.** How the nodes come to exist
and how the Kubernetes distribution is installed is written in
[`docs/runbook.md`](docs/runbook.md), and may use whatever tool suits the environment. This
repo takes over at the first thing that can be reconciled: the GitOps controller and its sync
root.

The boundary is deliberate. Everything after it is declarative, diffable and self-healing;
everything before it happens once per machine. Blurring the two produces a repo where half the
state drifts silently and the other half cannot.

## Features

> What this repo provides to everyone else. Engineering history belongs in
> [`CHANGELOG.md`](CHANGELOG.md), open work in [`TODO.md`](TODO.md).

- **A reproducible substrate.** Rebuildable from zero: the runbook for the machine layer, then
  the reconciler converges everything else. Versions pinned exactly, nothing applied by hand.
- **Cluster capabilities other repos depend on**: namespaces with enforced Pod Security
  Admission, the registry pull secret, the Gateway, the storage class, the certificate issuer,
  the secrets operator and its store. The full list is the contract in
  [`docs/contracts.md`](docs/contracts.md).
- **CI runners** that every other repo's pipeline runs on.

## The requirements contract

A platform repo declares what it needs in a `requirements.yaml`, in terms of **capabilities**
rather than implementations: *"a secret store reachable as `ClusterSecretStore/<name>`"*, not
*"deploy this particular secret manager with these values"*. How each one is satisfied is this
repo's business alone.

That split is what makes the boundary checkable. The consumer runs its own
`check-requirements.py` against the live cluster and gets a **named missing prerequisite**
before deploying, instead of a `CrashLoopBackOff` an hour later that nobody can attribute to a
side.

## Adopting this scaffold

1. Replace every placeholder: `@@PROJECT@@`, `@@PREFIX@@` (ticket prefix), `@@GROUP@@`
   (namespace), `@@DESCRIPTION@@`, `@@CI_TEMPLATES_PROJECT@@` and `@@CI_TEMPLATES_REF@@` (the
   shared CI-templates repo and the ref to track), `@@RUNNER_TAG@@` (the runner these
   pipelines run on). `grep -rnE '@{2}' .` must come back empty.
2. Run `./standard/compose.sh` to generate `CLAUDE.md`, and commit it.
3. Rename `clusters/<cluster>/` to the real cluster and list only the components that cluster
   actually runs. A sync root that pulls in the whole catalogue is how a laptop ends up
   running a production stack.
4. Work through `docs/runbook.md` on a throwaway environment — following it is how you find
   out what it is missing.

**Chicken-and-egg note:** this repo deploys the runner its own pipeline is tagged for. Until
that runner exists, point the tags in `.gitlab-ci.yml` at a hosted runner, bootstrap from the
runbook, then switch them back. Never remove the only working runner before its replacement
has actually executed a job — that mistake stops every pipeline in the group at once.

## Layout

```
clusters/<cluster>/            the sync root: which components THIS cluster runs
apps/<component>/
  ks.yml                       the reconciler's entry for the component
  app/                         its manifests, or a release plus values
repositories/                  pinned chart and image sources, by exact version
manifests/                     raw cluster prerequisites, validated by CI
docs/runbook.md                how to recover each component, and the machine-layer bootstrap
auto-tests/group-b, group-c    plan/verify scenarios and human methodologies
scripts/check-versions.py      what is pinned vs what is newest — input to the monthly audit
standard/                      the shared rulebook's sources + this repo's identity
```

## Working here

```bash
# Lint exactly what CI lints.
yamllint .
kubeconform -strict -summary manifests/

# Render what the reconciler would apply, and diff it against the live cluster.
flux build kustomization <name> --path clusters/<cluster>
kubectl diff -f manifests/

# There is no local apply step. Merging is the apply; the reconciler does the rest.
```

## Non-negotiables

- **Idempotent** — the second run changes nothing. Reconciliation, never a one-shot script.
- **Reproducible from zero** — an undocumented prerequisite is a defect.
- **Nothing applied by hand** — a `kubectl edit` is either reverted by the next reconcile or
  survives as invisible drift. If it matters, it is in git.
- **Pinned versions everywhere** — `latest` is an outage waiting for a quiet week.
- **Credentials from the environment**, never from a committed file.
- **Destructive operations are proposed, never executed autonomously** — print the command,
  let a human run it. Backups first for anything holding data.
- **Verification is the state of the system** — "applied successfully" is not verification;
  `Ready`, `Running`, `online`, "no drift" are.
