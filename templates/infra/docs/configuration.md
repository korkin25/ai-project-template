# Configuration — @@PROJECT@@

Two kinds of configuration live in this repo, and keeping them apart is what makes the repo
safe to read:

1. **Declared, committed values** — versions, host names, cluster settings. They are in
   `inventories/<env>/group_vars/` and are reviewed like code.
2. **Credentials** — never committed. They come from the operator's environment or from the
   secret store at run time. This document names **where each one originates**, which is the
   part that makes a rebuild-from-zero possible.

## Declared values (committed)

Per environment, in `inventories/<env>/group_vars/all.yml`:

| Variable | Example | Purpose |
|---|---|---|
| `cluster_name` | `laptop-local` | Identifies the environment; used in resource names and in the runbook. |
| `kubernetes_version` | `1.31.4` | Exact version of the distribution. Never a range: a range means the cluster that exists and the cluster this repo describes are different things. |
| `cert_manager_version` | `1.16.2` | Pinned chart version of the certificate operator. |
| `gateway_api_version` | `1.2.1` | Pinned version of the Gateway API CRDs. |
| `external_secrets_version` | `0.12.1` | Pinned chart version of the secrets operator. |

Application versions are **not** here — see [architecture.md](architecture.md).

## Credentials (never committed)

Every row states where the value comes from, because a bootstrap that depends on a value only
one person can produce is not reproducible.

| Credential | Used for | Origin | Lifetime |
|---|---|---|---|
| SSH private key | Ansible connecting to hosts | The operator's own key, in their agent. Never a shared key, never in this repo. | per operator |
| kubeconfig | `kubectl` / `helm` against the cluster | Generated during bootstrap; kept in the operator's `~/.kube/`. Git-ignored patterns exist so a stray copy cannot be committed. | rotate on staff change |
| Runner registration token | Registering the CI runner | GitLab → project/group → Settings → CI/CD → Runners. Single use; a new one is created rather than a stored one reused. | single use |
| Registry pull secret | Pulling images and OCI charts | Deploy token created in GitLab; seeded into the cluster during bootstrap and thereafter managed by the secrets operator. | rotate quarterly |
| Secret-store root credential | Bootstrapping the secrets operator | Created during bootstrap; stored in the team's password manager, never on disk. | rotate on staff change |

## Bootstrap order

The order matters — each step needs the previous one to exist:

1. Hosts reachable over SSH with the operator's key.
2. `ansible-playbook … playbooks/site.yml` provisions the machines and the cluster.
3. `kubectl apply -f manifests/` creates namespaces and cluster-scoped prerequisites.
4. The registry pull secret is seeded, so anything else can be pulled at all.
5. The secrets operator is installed and pointed at the secret store; from here on, secrets
   arrive in namespaces by reference and no human hands them around.
6. The GitOps controller is installed; the platform repo takes over application deployment.

Each step is a procedure in [runbook.md](runbook.md), and each one is approved separately.

## Rules

- **A credential is never printed, committed or pasted** — not into a log, not into an MR
  description, not into a chat. Treat any token that was ever displayed as compromised and
  rotate it.
- **A change to this file is a change to the bootstrap.** Keep it in the same commit as the
  code that reads the value; an undocumented variable is one a rebuild cannot supply.
- Secrets are seeded through the documented procedure only. Anything else is a hand-applied
  change, which this repo does not permit.
