
---

# Profile: infra

An **infra** repo provisions machines and cluster prerequisites — the substrate everything
else assumes. It contains no application code, builds no image, and publishes no package. Its
output is **applied configuration**: a cluster that exists, a runner that is registered, an
operator that is installed.

## What it owns

- Cluster bootstrap: the distribution, the CNI, the storage class, the Gateway/ingress.
- Cluster-wide platform components: cert-manager, the secrets operator, the secret store,
  reload controllers, monitoring CRDs.
- CI runners, and the credentials they need to exist at all.
- The GitOps controller itself, and its sync root.

## What it does NOT own

- **Which version of which application runs.** That is the platform repo's bundle. An infra
  repo that pins an application version has taken over a job it cannot do consistently.
- Any application chart or manifest.

The boundary is worth stating in `docs/architecture.md` in one sentence each way, because
"install the operator" and "deploy the app that needs the operator" look similar and end up
duplicated otherwise.

## Non-negotiables

- **Idempotent.** Running it twice changes nothing the second time. Every run is a
  reconciliation, never a one-shot script whose effect depends on prior state.
- **Reproducible from zero.** The repo must be able to build the substrate on a fresh
  machine. A step that only works because of undocumented existing state is a defect —
  write it down or automate it.
- **Nothing applied by hand.** A change made with `kubectl edit` and not committed here will
  be silently reverted by the reconciler, or worse, silently survive and diverge. If it
  matters, it is in git.
- **Pinned versions.** Every chart, operator, image and collection is referenced by an exact
  version. `latest` in an infra repo is an outage waiting for a quiet week.
- **Credentials come from the environment**, never from a committed file. Bootstrap secrets
  are seeded through a documented procedure that names where each value comes from — see
  `docs/configuration.md`.

## Safety

Infra changes are the least reversible in the platform: a bad CNI change costs the cluster,
and a bad runner change costs CI. Accordingly, beyond the base *Safe autonomy* rules:

- **Applying to a cluster always requires explicit human approval**, every time. Approval to
  apply once is never approval to apply again.
- **Destructive operations are proposed, never executed autonomously** — deleting a node,
  a namespace, a PVC, or anything holding state. Print the command; let a human run it.
- **Plan before apply.** Show the diff (`--check --diff`, `helm template`, `flux diff`) and
  what it would change, before asking.
- **Backups first** for anything holding data, and say where the backup is.

## Verification

An infra repo has no unit tests worth the name; verification is the *state of the system*:

- Every change is verified by reading back the real state — the node is `Ready`, the operator
  is `Running`, the runner reports `online`, the reconciler shows no drift.
- `AUTOPILOT-LOG.md` entries record that read-back verbatim under **Verified by**. "Applied
  successfully" is not verification; the resulting state is.
- Document, in `docs/runbook.md`, how to recover each component — that runbook is the real
  test, and it is exercised by following it, not by writing it.

## CI

`.gitlab-ci.yml` includes `/globals.yml` and `/sast.yml` (checkov and gitleaks matter most
here), plus linting for the provisioning tool in use. `ref:` follows the platform-wide choice recorded in the service profile — `main` today,
because the shared templates repo has no usable tag. It is a recorded decision, not an
oversight; check the tag actually carries every included file before changing it.

CI **lints and validates only — it never applies.** A pipeline holding cluster-admin
credentials is a larger risk than the manual step it saves.
