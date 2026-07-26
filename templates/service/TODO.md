# TODO — @@PROJECT@@

Open work only (⬜ planned, 🟡 in progress). A task that is done **and verified** moves to
[CHANGELOG.md](CHANGELOG.md) in the same change — this file is never a history.

## Current state / next action

Keep this block accurate: it is the cold-start entry point. A fresh session (or a different
agent) reads it and must know what to do without re-deriving anything.

- **State:** scaffolded from the `service` template; no feature implemented yet.
- **Next action:** substitute the scaffold placeholders, run `./standard/compose.sh`, push to
  `dev`, and read the first pipeline's logs — including the green jobs.

## Legend

⬜ Planned · 🟡 In progress · ✅ Done → moved to `CHANGELOG.md`

## Ticket ids

`@@PREFIX@@-<n>` for tasks, `@@PREFIX@@-D<n>` for decisions. Numbers are sequential within
this repo and **never reused**; the prefix is unique across the group, so an id can be cited
from another repo without qualification. Work spanning repos also carries a platform id
(`<PLATFORM>-<n>`), referenced from the local ticket:

| @@PREFIX@@-14 | 🟡 | Emit the v2 event shape | part of <PLATFORM>-7; consumer side is <OTHER>-3 |

## Open tasks

| Id | Status | Task | Details |
|---|---|---|---|
| _none_ | | | |

## Test status of the current feature

Per-test pass/fail for the feature in progress (the catalog itself lives in
[docs/tests.md](docs/tests.md)). A task is done only when every applicable tier passes —
never mark one done without the proof.

| Test | Tier | Status |
|---|---|---|
| _none in progress_ | | |

## Planned / ideas

A new request or idea from the user lands here first, becomes a `@@PREFIX@@-<n>` task above
when it is picked up, and is described in `README.md` `## Features` once it ships.

- _None yet._
