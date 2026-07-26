# Test plan — @@PROJECT@@

An infra repo has no unit tests worth the name. **Verification is the state of the system**,
and the tier model maps onto that as follows — the mapping is unusual enough to be worth
writing down, so nobody adds a hollow test suite to make this file look conventional.

| Tier | Here | Why |
|---|---|---|
| **(a) fully automated** | The CI pipeline itself: `yamllint`, `ansible-lint`, `ansible-playbook --syntax-check`, manifest validation, checkov, gitleaks. | These are the only checks that can run without touching a cluster. CI holds no credentials, so it can prove a change is *well-formed*, never that it *works*. |
| **(b) dev-machine / sandbox** | `--check --diff` runs, `helm template`, `flux diff`, and a rebuild in a throwaway environment. See [`../auto-tests/group-b/`](../auto-tests/group-b/). | Needs real access. Run by the agent in a sandbox, and by a human against a real environment before an apply. |
| **(c) human-in-the-loop** | Following [`runbook.md`](runbook.md) end to end. See [`../auto-tests/group-c/`](../auto-tests/group-c/). | The runbook is the real test of this repo, and it is exercised by following it — not by writing it. |
| **(d) cross-service e2e** | The **platform repo**. | Whether applications actually run on this substrate is a platform-level question. |

## Tier (a) — what CI proves on every push

| Check | What it asserts | Status |
|---|---|---|
| `yamllint` | No duplicate keys, no implicit octals, no accidental YAML booleans — the quirks that silently change meaning | ✅ |
| `ansible-lint` (production profile) | Idempotence patterns, FQCN module names, no floating versions | ✅ |
| `ansible-playbook --syntax-check` | Every playbook, role and include resolves — the "does it compile" check | ✅ |
| manifest validation | Every manifest parses and has `apiVersion`, `kind`, `metadata.name` (schema-validated when kubeconform is present) | ✅ |
| checkov | No permissive defaults in the manifests this repo owns | ✅ |
| gitleaks | No credential committed | ✅ |

**What tier (a) explicitly does NOT prove:** that the change works. CI never applies
anything, so a green pipeline means "well-formed", not "correct". Treating green as approval
to apply is the mistake this table exists to prevent.

## Tier (b) — before every apply

| Check | Command | Records |
|---|---|---|
| Plan is what you expect | `ansible-playbook -i inventories/<env> playbooks/site.yml --check --diff` | the diff, in the MR |
| Manifest delta | `kubectl diff -f manifests/` | the diff |
| GitOps delta | `flux diff kustomization <name> --path ./<path>` | the diff |
| Idempotence | run the playbook twice; the second run must report **zero changed** | the summary line |

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
