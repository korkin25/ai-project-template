# TODO

Single list of **open** work (statuses ⬜/🟡). Done tasks (✅) move to
[CHANGELOG.md](CHANGELOG.md) — see the rule below.

## Current state / next action

- Template initialized. **Next action:** adopt it — follow the checklist in
  [README.md](README.md) (rename the `app` package, set your `PRJ` ticket prefix, trim what
  you don't use), then log your first task here as `PRJ-1`.

## Legend

⬜ Planned · 🟡 In progress · ✅ Done → moved to `CHANGELOG.md`

## Maintenance rule

- As soon as a task becomes ✅, move its row from `TODO.md` into `CHANGELOG.md` under the
  matching `## [Unreleased]` subsection.
- If a section has no open tasks left after the move, delete it from `TODO.md`.
- Never mark a task ✅ without confirmation that it actually works (a passing test).

## Task IDs

Tasks use local identifiers `PRJ-<n>` (no external tracker required). Reference them in
discussions, commits, and PRs. Numbering is mandatory and IDs are never reused. Decision
items use `PRJ-D<n>`.

## Open tasks

_None — add rows as `| PRJ-<n> | ⬜ | <task> | <details> |`._
