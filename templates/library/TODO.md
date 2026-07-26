# TODO — @@PROJECT@@

Open work only (⬜ planned, 🟡 in progress). A task that is done **and verified** moves to
[CHANGELOG.md](CHANGELOG.md) in the same change — this file is never a history.

## Current state / next action

Keep this block accurate: it is the cold-start entry point. A fresh session (or a different
agent) reads it and must know what to do without re-deriving anything.

- **State:** scaffolded from the `library` template; the exported API is still the sample
  `Envelope`.
- **Next action:** substitute the scaffold placeholders, run `./standard/compose.sh`, then
  design the real public API **before** writing it — for a library the API shape is the
  architectural decision, and it needs the user's approval.

## Legend

⬜ Planned · 🟡 In progress · ✅ Done → moved to `CHANGELOG.md`

## Ticket ids

`@@PREFIX@@-<n>` for tasks, `@@PREFIX@@-D<n>` for decisions. Numbers are sequential within
this repo and **never reused**; the prefix is unique across the group, so a consuming repo
can cite an id directly. Work spanning repos also carries a platform id (`JAP-<n>`):

| @@PREFIX@@-14 | 🟡 | Add `Envelope.trace_id` | part of JAP-7; consumers are DISP-3, PROC-9 |

## Open tasks

| Id | Status | Task | Details |
|---|---|---|---|
| _none_ | | | |

## Consumer bumps in flight

A published version only matters once consumers move. **Never edit another repo's pin
yourself** — open a ticket there and track it here until it lands.

| Version | Consumer repo | Their ticket | Status |
|---|---|---|---|
| _none_ | | | |

## Test status of the current feature

| Test | Tier | Status |
|---|---|---|
| _none in progress_ | | |

## Planned / ideas

A new request or idea lands here first, becomes a `@@PREFIX@@-<n>` task when picked up, and
is described in `README.md` `## Features` once it ships.

- _None yet._
