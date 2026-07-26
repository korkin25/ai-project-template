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
   `flux build kustomization <name> --path clusters/<cluster>` renders what the controller
   would apply, `flux diff` and `kubectl diff -f manifests/` show it against the live cluster.
   A summary of the diff is not the diff.
2. **Merging is the apply.** For anything already under `clusters/`, the way to change the
   cluster is to change git and let the reconciler converge — the plan is what the reviewer
   reads. The exceptions are the bootstrap steps below, which run before there is a
   reconciler; those **require explicit human approval every time**, and approval to apply
   once is never approval to apply again. An agent proposes the command; a human runs it.
3. **Destructive operations are proposed, never executed autonomously.** Deleting a node, a
   namespace, a PVC or anything holding state: print the command, let a human run it.
4. **Backups first** for anything holding data, and say where the backup is before touching
   the thing it backs up.
5. **Verify by reading back the real state.** "Applied successfully" is not verification —
   the node is `Ready`, the operator is `Running`, the runner reports `online`, the
   reconciler shows no drift. That read-back is what goes in the log.

---

## Bootstrap: the machine layer

**This is the one procedure that is not reconciled, and therefore the one that must be
written down in full.** Everything else in this repo is recoverable by making git correct and
waiting; this part is recoverable only by someone following these steps.

The tool is deliberately unspecified — a cloud image, a config-management run, an installer
script, or a documented sequence of typed commands are all acceptable, because the choice
depends on the environment and none of it is diffable anyway. What is **not** optional is that
each step below is written concretely enough to be followed by someone who did not do it last
time, and that the versions are exact.

> Replace this block with the real procedure for this environment. A placeholder left here
> is the defect that turns a lost machine into a lost week.

```text
1. Machine exists.        <how: image/provider/hardware, and the exact OS version>
2. OS prerequisites.      <kernel modules, sysctls, swap, time sync, firewall openings>
3. Kubernetes installed.  <distribution and EXACT version — the one value with no home in
                           the GitOps tree, because nothing in-cluster can install it>
4. Node joined.           <how a second node joins, and where the join credential comes from>
5. kubeconfig retrieved.  <where it lands; it never enters this repo — see .gitignore>
```

**Verify before continuing** — the rest of this repo assumes all of it:

```bash
kubectl get nodes -o wide      # every node Ready, at the version you expect
kubectl version                # server version matches step 3 exactly
kubectl get pods -A            # the distribution's own components Running
```

Then continue at *Rebuild from zero*, step 2 — from that point the tree takes over.

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

# 2. Fix the machine layer, not the tree. A node is not reconciled from git: repeat the
#    machine-layer bootstrap above for this host, at the SAME exact versions the other nodes
#    run. A node that rejoins on a newer patch release is a fleet with two configurations and
#    an intermittent bug that follows one workload around.

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
# 1. Ask the reconciler what it thinks it has done. Its status is the diagnosis: a chart that
#    will not pull, a dependency never marked healthy and a failed upgrade look identical from
#    `kubectl get pods` and completely different here.
kubectl -n platform-system get pods,deploy
flux get kustomizations -A
flux get helmreleases -A
flux logs --level=error --since=1h

# 2. Re-drive reconciliation from git. This IS the recovery: the desired state, at the pinned
#    version, is already committed — the fix is to make the controller converge to it, never
#    to install the component by hand. Installing by hand produces a second writer, and the
#    next reconcile silently undoes whatever you just did.
flux reconcile kustomization <name> --with-source

# 3. If the release itself is wedged mid-upgrade, force a fresh apply of the SAME pinned
#    version. Note what this does NOT do: change a version. A recovery that upgrades is an
#    unplanned upgrade, during an incident, with no rollback tested.
flux suspend helmrelease <name> -n platform-system
flux resume  helmrelease <name> -n platform-system

# 4. Verify.
kubectl -n platform-system rollout status deploy/<name>
flux get helmreleases -A     # Ready=True, and the revision you expect
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
# (`@@RUNNER_TAG@@`). A tag mismatch looks exactly like an offline runner.

# 2. The deployment comes from apps/<component>/, so redeploying it is a reconcile — not a
#    hand-run install that the next reconcile would revert anyway.
flux reconcile kustomization <runner-component> --with-source

# 3. Re-register with a fresh token if the registration itself is gone. The token comes from
#    the documented source in docs/configuration.md — never from a committed file.
#    (Human step, requires approval: it creates a credential.)

# 4. Verify with a real pipeline, not with the UI's status dot.
```

---

## Recover: the GitOps controller and its sync root

**Symptom.** Changes merged to the platform repo do not appear in the cluster.

```bash
flux check
flux get sources all -A
flux get kustomizations -A
flux logs --level=error --since=1h

# Show the drift before touching it — this is the diff a human reads.
flux diff kustomization <name> --path clusters/<cluster>
```

**Check the source before the Kustomization.** The most common cause is not the controller at
all: the source is stuck on an old revision because the credential expired or the ref moved,
and every Kustomization downstream is then faithfully reconciling yesterday's git — reporting
`Ready=True` the entire time. `flux get sources` shows the revision actually fetched; compare
it against the commit you expected to see applied.

**Do not** fix drift with `kubectl edit`. A hand-edit is either reverted by the next
reconcile (and the time spent is wasted) or it survives and the cluster now differs from git
in a way nobody can see. If it matters, it goes in git.

---

## Rebuild from zero

The scenario this repo exists to make possible: an empty machine becomes the substrate.

Four hand-run steps, and then it stops being manual. That count is the point: everything after
step 4 arrives by reconciliation, so it cannot be forgotten, mistyped or done in the wrong
order.

```bash
# 1. The machine layer — follow "Bootstrap: the machine layer" above, and verify it there.
#    Nothing beyond the credentials in docs/configuration.md may be assumed to exist.

# 2. Cluster prerequisites: namespaces with their PSA labels, cluster-scoped RBAC.
kubectl diff -f manifests/          # what would change — read it
kubectl apply -f manifests/         # with approval

# 3. Seed the registry pull secret by hand. Unavoidable chicken-and-egg: until it exists,
#    nothing can be pulled — including the secrets operator that manages it afterwards.
#    docs/configuration.md names where the value comes from.

# 4. Install the GitOps controller and point it at this repo's sync root. LAST manual step.
flux check --pre
flux bootstrap <provider> --path clusters/<cluster>     # with approval; read the plan first

# 5. Nothing to run. The reconciler converges the rest in dependency order — secret store,
#    certificate issuer, Gateway, storage class, runners — and keeps it converged. Watch it:
flux get kustomizations -A --watch
```

Then the platform repo's sync root is added the same way, and application deployment becomes
its business. This repo never pins an application version.

**Verify the rebuild by reading the state back**, and paste that output into
`AUTOPILOT-LOG.md`:

```bash
kubectl get nodes -o wide
kubectl get pods -A | grep -v Running | grep -v Completed
flux get kustomizations -A
```

A step that only worked because of state left over from a previous life is a defect in this
runbook — fix the runbook in the same change, not next time.
