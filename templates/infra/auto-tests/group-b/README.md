# Group (b) — plan and verify against a real environment

Everything that needs real access: a render diffed against a live cluster, a reconcile watched
to completion, a rebuild in a throwaway environment. CI cannot run any of it, because CI
deliberately holds no credentials — which is why this directory carries most of this repo's
real verification.

## The plan/verify loop, which is the whole job

```bash
# 1. PLAN — never skipped, never summarised. The diff is what gets reviewed, and it is the
#    last thing a human sees before the cluster changes.
flux build kustomization <name> --path clusters/<cluster>   # what would be applied
flux diff kustomization <name> --path clusters/<cluster>    # against what is live
kubectl diff -f manifests/

# 2. MERGE — merging is the apply. Nothing is run locally; the reconciler converges from git.
#    (The exceptions are the bootstrap steps in docs/runbook.md, approved individually.)

# 3. VERIFY by reading the state back, once reconciliation has settled. This output is what
#    goes into AUTOPILOT-LOG.md; "merged successfully" is not verification.
flux get kustomizations -A
kubectl get nodes -o wide
kubectl -n platform-system get pods
```

## Scenarios worth keeping here

- **Idempotence check.** Reconcile twice against a real cluster; the second reconcile must
  show **no drift** — the revision unchanged, `Ready=True`, and `flux diff` empty.

  ```bash
  flux reconcile kustomization <name> --with-source
  flux reconcile kustomization <name> --with-source     # again, immediately
  flux get kustomizations -A                            # same revision, Ready=True
  flux diff kustomization <name> --path clusters/<cluster>   # must print nothing
  ```

  This is still the single most valuable test in an infra repo, and it cannot be faked. It
  matters more here than it did for a one-shot run, not less: the controller re-applies on a
  timer, so a component that reports a change every pass churns the cluster continuously and
  makes drift detection useless for everything else in it.
- **Rebuild from zero** in a throwaway environment, following `docs/runbook.md` verbatim —
  including the machine-layer bootstrap, which is the part no diff can check. Every step that
  needed knowledge not in the runbook is a defect fixed in the same session.
- **Drift detection.** With reconciliation settled, make a deliberate hand-edit and confirm it
  is reverted on the next pass. That proves the reconciler is actually in control rather than
  merely installed — a suspended Kustomization looks identical to a healthy one until you try
  this.
- **Restore from backup** for anything holding state, before you ever need it.

Same exit contract as tier (a) — `0` pass, `77` skip, anything else fail — for any script
added here, so a scenario stays promotable.

**Nothing in this directory may apply a destructive change autonomously.** Deleting a node, a
namespace or a PVC is proposed as a printed command; a human runs it.
