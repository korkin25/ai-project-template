# Configuration — @@PROJECT@@

Two kinds of configuration live in this repo, and keeping them apart is what makes the repo
safe to read:

1. **Declared, committed values** — versions, cluster settings, which components a cluster
   runs. They are in the GitOps tree itself and are reviewed like code. There is no separate
   configuration format to learn: the manifest *is* the configuration.
2. **Credentials** — never committed. They come from the operator's environment or from the
   secret store at run time. This document names **where each one originates**, which is the
   part that makes a rebuild-from-zero possible.

## Declared values (committed)

There is no `values` file that governs the repo as a whole; each value lives next to the
object it configures, so a grep for the value finds the thing it affects.

| Value | Where it lives | Why there |
|---|---|---|
| Which components a cluster runs | `clusters/<cluster>/kustomization.yml` | The one file that differs per cluster. Keeping it to a list of references means an environment cannot silently acquire a different *version* of something. |
| Chart and image sources | `repositories/` — `HelmRepository`, `OCIRepository` | One place to audit where code enters the cluster from. `scripts/check-versions.py` reads exactly these. |
| Pinned component versions | the `version` / `ref.tag` in each release under `apps/<component>/` | Never a range. A range means the cluster that exists and the cluster this repo describes are different things, and no diff will tell you so. |
| Component settings | `apps/<component>/app/` values and patches | Reviewed with the component, rolled back with it. |
| Cluster prerequisites | `manifests/` | Namespaces, PSA labels, cluster-scoped RBAC — the things that must exist before a reconciler can install anything. |

Two values that deliberately have no home here: the **Kubernetes version itself**, which
belongs to the machine layer and is recorded in [runbook.md](runbook.md) alongside how the
distribution is installed; and **application versions**, which belong to the platform repo —
see [architecture.md](architecture.md).

## Credentials (never committed)

Every row states where the value comes from, because a bootstrap that depends on a value only
one person can produce is not reproducible.

| Credential | Used for | Origin | Lifetime |
|---|---|---|---|
| Node access (SSH key or console) | The machine-layer bootstrap only — before a cluster exists there is nothing to reconcile against | The operator's own key, in their agent. Never a shared key, never in this repo. | per operator |
| kubeconfig | `kubectl diff`, `flux diff`, reading state back | Generated during the machine-layer bootstrap; kept in the operator's `~/.kube/`. Git-ignored patterns exist so a stray copy cannot be committed. | rotate on staff change |
| GitOps source credential | The reconciler pulling **this** repo | Deploy key or project access token with read-only scope, created when the controller is installed. Read-only is load-bearing: a controller that can write to its own source can be made to reconcile whatever it just wrote. | rotate on staff change |
| Runner registration token | Registering the CI runner | GitLab → project/group → Settings → CI/CD → Runners. Single use; a new one is created rather than a stored one reused. | single use |
| Registry pull secret | Pulling images and OCI charts | Deploy token created in GitLab; seeded into the cluster during bootstrap and thereafter managed by the secrets operator. | rotate quarterly |
| Secret-store root credential | Bootstrapping the secrets operator | Created during bootstrap; stored in the team's password manager, never on disk. | rotate on staff change |

## Bootstrap order

Bootstrap is the short prefix of hand-run steps that has to exist **before** there is a
reconciler to reconcile with. The order matters — each step needs the previous one:

1. **The machine layer.** Nodes exist, the distribution is installed, a kubeconfig is in hand.
   Outside the GitOps tree, by any tool; the procedure is in [runbook.md](runbook.md).
2. `kubectl apply -f manifests/` — namespaces with their PSA labels and the cluster-scoped
   prerequisites. Created here rather than by whichever chart installs first, because a
   namespace owned by a chart disappears with that chart.
3. **The registry pull secret is seeded by hand.** This is the one unavoidable
   chicken-and-egg: nothing can be pulled until it exists, including the secrets operator that
   would otherwise manage it.
4. **The GitOps controller is installed and pointed at `clusters/<cluster>/`.** This is the
   last hand-applied step — everything after it is a merge.

From there the reconciler converges the rest in dependency order (secret store, certificate
issuer, Gateway, storage class, runners) and keeps it converged. The platform repo's own sync
root is added the same way, and application deployment becomes its business.

Steps 1–4 are procedures in [runbook.md](runbook.md) and each one is approved separately —
approval to apply once is never approval to apply again. **Keeping this list short is a
design goal**, not an accident of maturity: each hand-run step is state that no diff can show
you, and it is the part of a rebuild that is discovered to be wrong at 03:00.

## Rules

- **A credential is never printed, committed or pasted** — not into a log, not into an MR
  description, not into a chat. Treat any token that was ever displayed as compromised and
  rotate it.
- **A change to this file is a change to the bootstrap.** Keep it in the same commit as the
  manifest that consumes the value; an undocumented credential is one a rebuild cannot supply,
  and it is discovered missing only when the rebuild is already needed.
- Secrets are seeded through the documented procedure only. Anything else is a hand-applied
  change, which this repo does not permit.
