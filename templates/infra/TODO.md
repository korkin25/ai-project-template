# TODO — @@PROJECT@@

Open work only (⬜ planned, 🟡 in progress). A task that is done **and verified** moves to
[CHANGELOG.md](CHANGELOG.md) in the same change — this file is never a history.

In this repo "verified" has a specific meaning: the state was **read back** (the node is
`Ready`, the operator is `Running`, the runner reports `online`, the reconciler shows no
drift). "Applied successfully" does not close a task here.

## Current state / next action

Keep this block accurate: it is the cold-start entry point, and in an infra repo it is often
read during an incident.

- **State:** scaffolded from the `infra` template; the GitOps tree is empty and nothing is
  reconciled yet.
- **Next action:** substitute the scaffold placeholders, run `./standard/compose.sh`, rename
  `clusters/<cluster>/` to the real cluster and list only the components it actually runs,
  then write the machine-layer bootstrap into `docs/runbook.md` and walk that runbook on a
  throwaway environment — following it is how you find out what it is missing.

## Legend

⬜ Planned · 🟡 In progress · ✅ Done → moved to `CHANGELOG.md`

## Ticket ids

`@@PREFIX@@-<n>` for tasks, `@@PREFIX@@-D<n>` for decisions. Sequential, never reused. Infra
ids are cited from other repos more often than most ("blocked on @@PREFIX@@-12, the runner"),
so the prefix must be unique across the group. Cross-repo work also carries a platform id:

| @@PREFIX@@-14 | 🟡 | Install the Gateway API CRDs | unblocks JAP-7; consumers are SVC-3, SVC-9 |

## Open tasks

| Id | Status | Task | Details |
|---|---|---|---|
| _none_ | | | |

## Awaiting reconciliation, or a human step

Two kinds of change land here, and both are cases where "merged" is not yet "true of the
cluster":

- **Merged, not yet converged.** The reconciler applies on its own schedule and can fail
  while doing so. A change is closed when the read-back says so, not when the MR does.
- **Waiting on a human step** — anything in the machine layer or the bootstrap prefix
  (`docs/configuration.md`), which no merge can perform.

| Id | Change | Plan reviewed | Converged / applied — read-back |
|---|---|---|---|
| _none_ | | | |

## Planned / ideas

- _None yet._
