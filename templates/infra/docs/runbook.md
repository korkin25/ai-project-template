# Runbook — @@PROJECT@@

**This document is the real test of this repository.** An infra repo has no unit tests worth
the name: verification is the state of the system, and the proof that a component is
understood is that someone else can recover it from here at 03:00 without the person who
built it.

It is exercised by **following it**, not by writing it. A procedure that has never been run
is a hypothesis. Run each one at least once — in the local environment if nowhere else — and
record the run in `AUTOPILOT-LOG.md` under **Verified by** with the real output.

## Ground rules for every procedure below

1. **Plan before apply.** Show what would change and read it:
   `ansible-playbook … --check --diff`, `helm template`, `flux diff`, `kubectl diff -f`.
2. **Applying to a cluster requires explicit human approval, every time.** Approval to apply
   once is never approval to apply again — an agent proposes the command and a human runs it.
3. **Destructive operations are proposed, never executed autonomously.** Deleting a node, a
   namespace, a PVC or anything holding state: print the command, let a human run it.
4. **Backups first** for anything holding data, and say where the backup is before touching
   the thing it backs up.
5. **Verify by reading back the real state.** "Applied successfully" is not verification —
   the node is `Ready`, the operator is `Running`, the runner reports `online`, the
   reconciler shows no drift. That read-back is what goes in the log.

---

## Recover: a cluster node

**Symptom.** `kubectl get nodes` shows the node `NotReady`, or it is gone entirely.

**Blast radius.** Pods on that node are rescheduled; anything with local storage on it is
lost unless it was backed up.

```bash
# 1. Diagnose before changing anything — a node that is NotReady for a full disk needs a
#    different fix than one whose kubelet crashed, and rebuilding hides the cause.
kubectl describe node <node>
ssh <node> 'systemctl status kubelet; df -h; journalctl -u kubelet --since -1h | tail -50'

# 2. Re-run provisioning for that host only. It is idempotent: on a healthy host this is a
#    no-op, which is also how you confirm the playbook still matches reality.
ansible-playbook -i inventories/<env> playbooks/site.yml --limit <node> --check --diff
#    Read the diff. Then, with approval:
ansible-playbook -i inventories/<env> playbooks/site.yml --limit <node>

# 3. Verify by reading the state back.
kubectl get node <node> -o wide
kubectl get pods -A --field-selector spec.nodeName=<node>
```

**If the node must be replaced:** provision the new host, join it, and only then drain and
remove the old one — in that order, so capacity never dips below what the workloads need.
`kubectl drain <node> --ignore-daemonsets` is a **proposed** command: a human runs it.

---

## Recover: a cluster-wide component (operator, controller, CRDs)

**Symptom.** The operator's pods are not `Running`, or resources it owns stop reconciling.

```bash
# 1. What is actually deployed, and at which version?
kubectl -n platform-system get pods,deploy
helm -n platform-system list

# 2. Reinstall at the PINNED version from inventories/<env>/group_vars/all.yml. Never
#    "whatever is latest" — that turns a recovery into an unplanned upgrade, during an
#    incident, with no rollback tested.
helm upgrade --install <name> <chart> --version <pinned> -n platform-system --atomic

# 3. Verify.
kubectl -n platform-system rollout status deploy/<name>
kubectl get crd | grep <name>
```

**CRDs are the trap.** Helm does not upgrade or delete CRDs, and deleting a CRD deletes every
custom resource of that kind in the cluster — silently and irreversibly. Never `kubectl
delete crd` as a troubleshooting step.

---

## Recover: the CI runner

**Symptom.** Pipelines sit in `pending` with no runner picking them up.

This is the circular one worth practising: **the runner is what CI needs in order to fix
anything, including itself**. It is therefore always recoverable by hand from a workstation,
never only through a pipeline.

```bash
# 1. Is it registered and online?
kubectl -n platform-system get pods -l app=gitlab-runner
kubectl -n platform-system logs -l app=gitlab-runner --tail=100
# GitLab UI: Settings -> CI/CD -> Runners; the tag must match the one in .gitlab-ci.yml
# (`job-agent-local`). A tag mismatch looks exactly like an offline runner.

# 2. Re-register with a fresh token if the registration is gone. The token comes from the
#    documented source in docs/configuration.md — never from a committed file.
#    (Human step, requires approval: it creates a credential.)

# 3. Verify with a real pipeline, not with the UI's status dot.
```

---

## Recover: the GitOps controller and its sync root

**Symptom.** Changes merged to the platform repo do not appear in the cluster.

```bash
flux check
flux get sources oci -A
flux get kustomizations -A
flux logs --level=error --since=1h

# Show the drift before touching it — this is the diff a human approves.
flux diff kustomization <name> --path ./<path>
```

**Do not** fix drift with `kubectl edit`. A hand-edit is either reverted by the next
reconcile (and the time spent is wasted) or it survives and the cluster now differs from git
in a way nobody can see. If it matters, it goes in git.

---

## Rebuild from zero

The scenario this repo exists to make possible: an empty machine becomes the substrate.

```bash
# 1. Prerequisites: the machine is reachable and the operator has the credentials listed in
#    docs/configuration.md. Nothing else may be assumed to exist.
# 2. Provision the hosts.
ansible-playbook -i inventories/<env> playbooks/site.yml --check --diff   # read the plan
ansible-playbook -i inventories/<env> playbooks/site.yml                  # with approval
# 3. Apply the cluster prerequisites.
kubectl diff -f manifests/          # what would change
kubectl apply -f manifests/         # with approval
# 4. Seed the bootstrap secrets (docs/configuration.md names where each value comes from).
# 5. Install the GitOps controller; from here the platform repo takes over and deploys the
#    applications. This repo never pins an application version.
```

**Verify the rebuild by reading the state back**, and paste that output into
`AUTOPILOT-LOG.md`:

```bash
kubectl get nodes -o wide
kubectl get pods -A | grep -v Running | grep -v Completed
flux get kustomizations -A
```

A step that only worked because of state left over from a previous life is a defect in this
runbook — fix the runbook in the same change, not next time.
