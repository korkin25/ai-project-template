# Group (b) — plan and verify against a real environment

Everything that needs real access: a plan against a live cluster, a `--check --diff` run, a
rebuild in a throwaway environment. CI cannot run any of it, because CI deliberately holds no
credentials — which is why this directory carries most of this repo's real verification.

## The plan/verify loop, which is the whole job

```bash
# 1. PLAN — never skipped, never summarised. The diff is what gets reviewed.
ansible-playbook -i inventories/<env> playbooks/site.yml --check --diff
kubectl diff -f manifests/
flux diff kustomization <name> --path ./<path>

# 2. APPLY — a human step, approved every time (see docs/runbook.md).

# 3. VERIFY by reading the state back. This output is what goes into AUTOPILOT-LOG.md;
#    "applied successfully" is not verification.
kubectl get nodes -o wide
kubectl -n platform-system get pods
flux get kustomizations -A
```

## Scenarios worth keeping here

- **Idempotence check.** Run the playbook twice against a real host; the second run must
  report **zero changed**. This is the single most valuable test in an infra repo, and it
  cannot be faked — a task that always reports "changed" makes every future diff meaningless.
- **Rebuild from zero** in a throwaway environment, following `docs/runbook.md` verbatim.
  Every step that needed knowledge not in the runbook is a defect fixed in the same session.
- **Drift detection.** After an apply, confirm the reconciler reports no drift; then make a
  deliberate hand-edit and confirm it is reverted. That proves the reconciler is actually in
  control, rather than merely installed.
- **Restore from backup** for anything holding state, before you ever need it.

Same exit contract as tier (a) — `0` pass, `77` skip, anything else fail — for any script
added here, so a scenario stays promotable.

**Nothing in this directory may apply a destructive change autonomously.** Deleting a node, a
namespace or a PVC is proposed as a printed command; a human runs it.
