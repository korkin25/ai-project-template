# Group (b) — plan and verify against a real environment

Everything that needs real access but is not a cross-service test: the cluster checked against
`requirements.yaml`, a render diffed against what is actually live, a reconcile watched to
completion. CI cannot run any of it, because CI deliberately holds no deploy credential.

The distinction from [`../../e2e/`](../../e2e/) is worth keeping sharp, because both need a
cluster: **group (b) verifies that this repo's statement about an environment is true**
(the right versions, the right values, converged); **tier (d) verifies that the services in it
work together**. A promotion needs both, and they fail for entirely different reasons.

## The plan/verify loop, which is the whole job

```bash
# 1. PLAN — never skipped, never summarised. The rendered diff is what gets reviewed, and it
#    is the last thing a human sees before the environment changes.
python3 scripts/validate-bundles.py
python3 scripts/render.py clusters/<cluster>/environments/<env>
flux diff kustomization <name> --path clusters/<cluster>/environments/<env>

# 2. MERGE — merging is the deployment. Nothing is applied from here; Flux reconciles from
#    git. A version bump needs human approval every time.

# 3. VERIFY by reading the state back, once reconciliation has settled. This output is what
#    goes into AUTOPILOT-LOG.md; "merged successfully" is not verification.
flux get kustomizations -A
kubectl -n <namespace> get helmrelease
kubectl -n <namespace> get pods
```

## Scenarios worth keeping here

- **Prerequisites, before anything else.**

  ```bash
  python3 scripts/check-requirements.py --context <cluster>
  ```

  Run it against every environment's cluster, not only the one being changed. Treat
  `UNVERIFIED` as a question, never as a pass — it is what the script prints for a capability
  that cannot be probed without assuming an implementation, and a confident guess there would
  be a false failure for every other valid way of satisfying it.

- **The deployed version is the pinned version.** Read the version back from the running
  workload (its `/health`, its image tag, its `HelmRelease` status) and compare it to the
  bundle. They diverge more often than anyone expects: a failed reconcile leaves the previous
  release running while git says otherwise, and nothing shouts about it.

- **Values actually arrived.** Render, then compare the values Flux reports on the release
  against `values/common.yaml` + `values/<name>.yaml`. A key at the wrong nesting level is
  accepted by Helm and silently ignored — the deploy is green and the setting is not applied.

- **Secrets resolved.** Every `ExternalSecret` in the environment reports `SecretSynced`, and
  the resulting `Secret` has the keys the chart expects. This is the failure that looks like an
  application bug: the pod starts, reads an empty value, and fails somewhere unrelated.

- **A reconcile is idempotent.** Reconcile twice; the second pass must report no change. A
  release that reports a change on every pass makes drift detection useless for the whole
  environment, because "something changed" stops meaning anything.

Same exit contract as the other groups — `0` pass, `77` skip, anything else fail — for any
script added here, so a scenario stays promotable into a job later.

**Nothing in this directory may apply a destructive change autonomously.** Deleting a
namespace, a PVC or a release is proposed as a printed command; a human runs it.
