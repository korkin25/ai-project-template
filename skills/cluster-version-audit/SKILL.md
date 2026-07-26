---
name: cluster-version-audit
description: Audit and plan upgrades for CLUSTER SUBSTRATE — the CNI, cert-manager, the secrets operator, Vault, GitOps controllers, CRDs and operators that everything else runs on. Use monthly, or when asked to check whether cluster infrastructure is up to date, prepare a cluster upgrade, or review changelogs for infrastructure components. NOT for application data services — those have their own skill (data-plane-version-audit).
---

# Cluster version audit

Pinning versions is what makes a cluster reproducible. It is also what makes it quietly age
until an upgrade is no longer a step but a project. This runs monthly to keep that gap small
enough to cross.

**Scope: the substrate.** The CNI, cert-manager, the secrets operator, the secret store, the
GitOps controller, admission controllers, CRDs, operators. Things whose failure takes the
cluster with them. Databases, message buses and vector stores are **not** in scope — their
failure mode is losing data rather than losing the cluster, which needs a different order of
operations. Use `data-plane-version-audit` for those.

## Report, then stop

This skill produces **a plan, not an upgrade**. Applying to a cluster requires explicit human
approval every time; approval to apply once is never approval to apply again. Print the
commands; let a human run them.

## Steps

### 1. Collect the current state

Run this **from the root of the repository that owns the pins** — the infra or platform repo
whose manifests declare them — not from wherever this skill was installed. The version reader
ships with that repo, at `scripts/check-versions.py` — the `infra` scaffold provides one, and
any other repo holding pins is expected to provide its own at the same path. It reads Flux
`HelmRepository` / `OCIRepository` / `HelmRelease` versions and in-manifest image tags out of
the tree, so run anywhere else it reports an empty table, which reads identically to
"everything is current".

```bash
./scripts/check-versions.py            # what is pinned vs what is newest
./scripts/check-versions.py --json     # keep this: it is the before-picture
flux get kustomizations                # everything must be Ready BEFORE you plan an upgrade
kubectl get nodes -o wide
```

**If that repo has no `scripts/check-versions.py`, do not skip the step and do not write one
mid-audit.** Collect the same picture by hand — the pins from the manifests, then
`helm show chart <oci-url>` and `helm search repo <repo>/<chart>` for what is newest — and say
in the report that the before-picture was assembled manually. An audit whose first step was
quietly skipped is indistinguishable from one whose first step found nothing.

If anything is already NotReady, say so **first and prominently**, then carry on with the
audit. A pre-existing failure changes what the plan is worth — upgrading on top of a broken
reconciliation means you will not know which failure you caused — but it is a caveat to state,
not a reason to withhold the version analysis the user asked for.

### 2. Classify each gap by what it can break, not by SemVer

The version distance is a hint, not the risk. Sort by blast radius:

| Component | What an upgrade actually risks |
|---|---|
| CNI | pod networking cluster-wide, mid-upgrade. Nothing recovers on its own |
| CRD-bearing operator | a stored-version migration; the old CRs may stop being readable |
| cert-manager | issuance stops silently — existing certs keep working until they expire |
| secrets operator | secrets stop refreshing; existing Secrets persist, so it looks fine for hours |
| Vault | a restart comes back **sealed** unless auto-unseal is configured. Everything downstream stops |
| GitOps controller | you lose the tool you would use to roll back |

A patch bump to the CNI deserves more care than a major bump to something with no consumers.

### 3. Read the changelogs — actually read them

For every component that moved, fetch its release notes between the pinned and the latest
version. Look specifically for:

- **Breaking changes and removals**, including values renamed in the chart.
- **CRD changes**: a new stored version, a removed API version. Check what the cluster
  currently stores: `kubectl get crd <name> -o jsonpath='{.status.storedVersions}'`.
- **Required upgrade order** — many operators say "apply CRDs first"; a chart upgrade that
  skips that step half-applies and leaves the operator crash-looping.
- **Minimum Kubernetes version.** Compare against the actual server version, not the docs'
  assumption.

Do not skip intermediate majors when the vendor documents a stepped path. Say so if one is
required — jumping it is how a cluster gets stuck between two schemas.

### 4. Write the plan

One entry per component, ordered so nothing upgrades before its dependency:

```
<component>  <pinned> -> <target>
  risk:      what breaks if this goes wrong
  changelog: the specific entries that matter, quoted, with the link
  order:     what must be upgraded first, and why
  verify:    the command that proves it worked, and the expected output
  rollback:  how to get back, and whether the old version can still read the new state
```

**Report every component, including the ones you would not upgrade.** A rollback you cannot
describe is a *finding*, written into the entry as `rollback: NONE FOUND` with what you
checked — never a reason to leave the row out. Withholding a row makes the decision instead
of informing it, and the person deciding cannot see what they were not shown.

Add a separate `recommendation:` line saying what you would do and why. It is advice sitting
next to the evidence, not a filter applied before it.

### 5. Hand it over

Record the plan in the repository (`docs/` or the ticket), add an `AUTOPILOT-LOG.md` entry
with the before-picture attached, and report to the user with:

- **every** component that moved, with its full entry — not a summary that drops the
  awkward ones;
- what you recommend and why, clearly marked as a recommendation;
- anything you could **not** resolve — an unreachable source is a supply-chain problem worth
  raising on its own, not a blank cell in a table.

The deliverable is the complete analysis. The decision is the user's, and they need
everything you found in order to make it — including the parts that argue against acting.

## Guardrails

- **Never apply.** No `helm upgrade`, no `kubectl apply`, no `flux reconcile --with-source`
  against a live cluster. The plan is the deliverable.
- **Never bump a pin as a side effect of auditing.** Editing manifests is a separate,
  reviewed change.
- **Never filter the report.** Rank, annotate and recommend freely; omit nothing. "I judged
  this not worth mentioning" is the one output this skill must never produce.
- **Report unknowns as unknown.** Container image tags cannot be ordered reliably across
  registries; say "not resolved" rather than guessing, because a guessed "latest" is how a
  downgrade gets recommended.
- **One component per change** when the plan is eventually executed. A batch upgrade that
  breaks tells you nothing about which part broke.
- If the audit tool itself errors, fix the tool and re-run before reporting. A verifier
  nobody checked is worse than no verifier, because it is believed. A tool that is **absent**
  is a different case: read the pins by hand and say so — do not write a version checker
  during an audit, because a checker nobody has ever verified is exactly that believed
  verifier, and it arrives wearing the authority of the report.
