# Group (b) — dev-machine / AI-sandbox scenarios

Tests that **cannot** run in CI: they need a real broker, a real database, credentials that
must not live in a pipeline, or a judgement call about the result. The agent runs them
itself in an isolated sandbox during development, and again after a release once CI is
green.

They are not in `group-a/` because a test that needs a secret CI does not have would either
fail every pipeline or be skipped in every pipeline — and a permanently skipped test is a
test nobody notices has rotted.

## Conventions

- One file per scenario, named after what it proves (`replay-after-crash.sh`).
- Same exit contract as group (a): `0` pass, `77` skip, anything else fail. Keeping the
  contract identical means a scenario can be promoted into `group-a/` by moving the file
  once its prerequisites exist in CI.
- Every scenario states, at the top, **which prerequisites it needs and where they come
  from** (`docs/configuration.md`). A scenario that fails because of an unset variable must
  say so and exit 77.
- Record the run and its result in `TODO.md` while the feature is open, and in
  `AUTOPILOT-LOG.md` under **Verified by** when it is done — with the real output, not
  "ran successfully".

## Suggested scenarios for this service

- Redelivery: kill the process between processing and commit; the message must reappear and
  the second run must be a no-op (idempotency).
- Backpressure: a source that produces faster than the worker drains; memory must stay flat.
- Config failure: an invalid value must stop the process at startup with a readable message.
