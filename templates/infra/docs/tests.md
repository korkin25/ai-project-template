# Test plan — @@PROJECT@@

An infra repo has no unit tests worth the name. **Verification is the state of the system**,
and the tier model maps onto that as follows — the mapping is unusual enough to be worth
writing down, so nobody adds a hollow test suite to make this file look conventional.

| Tier | Here | Why |
|---|---|---|
| **(a) fully automated** | The CI pipeline itself: `yamllint`, rendering every sync root, `kubeconform` on `manifests/`, checkov, gitleaks. | These are the only checks that can run without touching a cluster. CI holds no credentials, so it can prove a change is *well-formed*, never that it *works*. |
| **(b) dev-machine / sandbox** | `flux build`, `flux diff`, `kubectl diff -f manifests/`, and a rebuild in a throwaway environment. See [`../auto-tests/group-b/`](../auto-tests/group-b/). | Needs real access. Run by the agent in a sandbox, and by a human reading the plan before merging. |
| **(c) human-in-the-loop** | Following [`runbook.md`](runbook.md) end to end. See [`../auto-tests/group-c/`](../auto-tests/group-c/). | The runbook is the real test of this repo, and it is exercised by following it — not by writing it. |
| **(d) cross-service e2e** | The **platform repo**. | Whether applications actually run on this substrate is a platform-level question. |

## Tier (a) — what CI proves on every push

| Check | What it asserts | Status |
|---|---|---|
| `yamllint` | No duplicate keys, no implicit octals, no accidental YAML booleans — the quirks that silently change meaning | ✅ |
| render every sync root (`flux build`, or `kustomize build` as fallback) | Every overlay, patch and remote base resolves. This repo's "does it compile": it catches the missing resource and the mistyped patch target that would otherwise surface mid-reconcile, with the cluster already half-changed | ✅ |
| `kubeconform -strict` on `manifests/` | Every object validates against the real Kubernetes schemas, offline. `-strict` is the load-bearing flag: without it a typo'd key is accepted and silently ignored by the API server | ✅ |
| checkov | No permissive defaults in the manifests this repo owns | ✅ |
| gitleaks | No credential committed | ✅ |

**What tier (a) explicitly does NOT prove:** that the change works. CI never applies
anything, so a green pipeline means "well-formed", not "correct". Treating green as approval
to apply is the mistake this table exists to prevent.

## Tier (b) — before every merge

Merging is the apply, so this is the last point at which a human sees the change before the
cluster does.

| Check | Command | Records |
|---|---|---|
| Renders to what you expect | `flux build kustomization <name> --path clusters/<cluster>` | the rendered output, skimmed |
| GitOps delta | `flux diff kustomization <name> --path clusters/<cluster>` | the diff, in the MR |
| Manifest delta | `kubectl diff -f manifests/` | the diff |
| Idempotence | reconcile twice; the second reconcile must show **no drift** | the `flux get kustomizations` read-back |

**Idempotence has not become less important — it has changed owner.** It used to be a property
of a run you chose to repeat; under a reconciler it is a property of every reconcile, on a
timer, forever. A component that reports a change on every pass makes drift detection useless
for the whole cluster, because "something changed" stops meaning anything.

## Tier (c) — periodically, and after any structural change

| Methodology | Why a human |
|---|---|
| Rebuild from zero, following `runbook.md` | Proves the runbook is complete. A procedure that has never been followed is a hypothesis. |
| Recover each component from `runbook.md` | Each recovery is only credible once someone other than its author has done it. |

## Recording results

Every verification is recorded in `AUTOPILOT-LOG.md` under **Verified by**, with the real
read-back output. "Applied successfully" is not verification — the resulting state is:

```
kubectl get nodes -o wide
kubectl -n platform-system get pods
flux get kustomizations -A
```
