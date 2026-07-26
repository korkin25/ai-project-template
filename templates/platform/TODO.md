# TODO — @@PROJECT@@

Open work only (⬜ planned, 🟡 in progress). A task that is done **and verified** moves to
[CHANGELOG.md](CHANGELOG.md) in the same change — this file is never a history.

In this repo "verified" has a specific meaning: the state was **read back** from the
environment (`flux get kustomizations -A`, the `HelmRelease` is `Ready`, the workload reports
the version that was pinned). "Merged" does not close a task here — merging only starts the
reconcile, and a reconcile can fail.

## Current state / next action

Keep this block accurate: it is the cold-start entry point, and in a platform repo it is what
someone reads while an environment is misbehaving.

- **State:** scaffolded from the `platform` template. One example cluster with a `dev`
  environment and a single placeholder service; nothing has been deployed.
- **Next action:** substitute the scaffold placeholders and run `./standard/compose.sh`; rename
  `clusters/example-cluster/` to the real cluster and the `example-*` values inside it; cut
  `requirements.yaml` down to what this platform actually needs, then run
  `python3 scripts/check-requirements.py --context <cluster>` and open the gaps as tickets in
  the infra repo — before the first bundle bump, not after it fails.

## Legend

⬜ Planned · 🟡 In progress · ✅ Done → moved to `CHANGELOG.md`

## Ticket ids

`@@PREFIX@@-<n>` for tasks, `@@PREFIX@@-D<n>` for decisions. Sequential, never reused.

**These are the platform ids.** Work that spans repos is planned here and cited from every
participating repo's own ticket, so an id in this file is quoted in places nobody in this repo
will ever look. Never renumber one.

| @@PREFIX@@-14 | 🟡 | Promote `<service>` 1.4.0 dev → stage | tier-(d) green in dev; local tickets SVC-3, SVC-9 |

## Open tasks

| Id | Status | Task | Details |
|---|---|---|---|
| _none_ | | | |

## Awaiting reconciliation, or an approval

Three kinds of change land here, and in all three "merged" is not yet "true of the
environment":

- **Merged, not yet converged.** Flux applies on its own schedule and can fail while doing so.
- **Waiting on a promotion approval** — a version bump is a deployment; someone has to say yes.
- **Blocked on another repo** — a service that has not published the version yet, or an infra
  prerequisite that is not satisfied. Name the repo and the ticket, not just "blocked".

| Id | Change | Approved by | Converged — read-back |
|---|---|---|---|
| _none_ | | | |

## Contract changes in flight

A contract change is not finished when the producer merges. Track the whole crossing here
until every consumer has moved and `docs/contracts.md` matches reality, because this is the
only repo that can see both ends of it.

| Id | Contract | Producer | Consumers moved | Tier-(d) updated |
|---|---|---|---|---|
| _none_ | | | | |

## Planned / ideas

- _None yet._
