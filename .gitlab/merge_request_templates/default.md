<!--
GitLab applies the template named `Default` to every new merge request automatically; the
others in this directory are opt-in from the description dropdown. If your instance does not
pick this one up, the file name is the thing to check first.

The GitHub twin is `.github/PULL_REQUEST_TEMPLATE.md`. Keep the two SAYING THE SAME THING: a
checklist that is stricter on one host teaches people that the review bar depends on where
the change happened to land.

Merge only when CI is green. Feature branches target `dev`; `dev` -> `rc` -> `release` is a
separate, approval-gated promotion, never something a feature MR does on its way past.
See CLAUDE.md § Per-task lifecycle.
-->

## What & why

<What changed, and why it had to change — not a restatement of the diff. Name the `PRJ-<n>`
this closes, and the platform id if the work spans repos.>

## Checklist

Tick what applies; **say why** next to anything you struck out. An unticked box with a reason
is a review conversation. A ticked box that was not true is the reason nobody trusts the list.

- [ ] **Design was written before any code or test** — data model, public API/contract,
      deployment shape, and the trade-off against the alternatives — in `docs/architecture.md`
      or the ticket. Any architectural decision was approved by the user first. Anything that
      moves a cross-repo contract is architectural by definition.
- [ ] **Logged in `TODO.md` as `PRJ-<n>` before the work started**, its status kept current
      while it ran, and the row **moved to `CHANGELOG.md`** now that it is done and verified —
      not marked done and left in place. If it is user-facing it is described in `README.md`
      `## Features`; engineering, CI, release and governance work never goes there.
- [ ] **Tests first, and all four tiers accounted for** — each listed in `docs/tests.md` and
      tagged. **(a)** automated, green in CI, and the run logs actually read *even though they
      are green*; **(b)** dev/sandbox tests run by the agent; **(c)** a human-in-the-loop
      methodology written and handed to the user; **(d)** cross-service e2e updated **in the
      platform repo in the same change set** (a separate MR there, linked by the platform id).
      A tier that does not apply is written down as N/A with its reason — an unmentioned tier
      is indistinguishable from a forgotten one.
- [ ] **Observability shipped in this change, not as a follow-up.** The metrics that make
      *this feature* diagnosable (not just rate/errors/duration on the endpoint), structured
      log fields as queryable metadata rather than text interpolated into the message, the
      panel, and `docs/observability.md` saying what each metric means and what a bad value
      looks like. The metrics were confirmed to actually appear — an emitter nobody checked is
      indistinguishable from one that silently emits nothing.
- [ ] **`docs/contracts.md` updated** if this change touched anything outside this repo
      consumes — an exported symbol, an endpoint, a topic and its schema, a table this repo
      writes, or the vendored `standard/` and `templates/` surface. Propagation to the
      consuming repos is part of *this* change, not a follow-up ticket: between the edit here
      and the last repo's update, the group is running two versions of the contract and
      neither is authoritative.
- [ ] **Docs in lockstep, in this change** — `README.md`, `docs/*`, `docs/configuration.md`
      for a new or renamed env var, `CHANGELOG.md` under `## [Unreleased]`.
- [ ] **`AUTOPILOT-LOG.md` entry added** if this was an autonomous change of any substance.
- [ ] **`doc-sync` is green.** It fails an MR that moves the code/deploy/standard surface
      without touching a doc. If this change genuinely needs none, use the escape hatch
      deliberately — the `no-docs` label, or `[skip doc-sync]` in the MR title — and say here
      why. Reaching for it by reflex is how the gate stops meaning anything.
- [ ] **`standard-drift` is green.** `CLAUDE.md` is **generated** by `./standard/compose.sh`
      from `standard/base.md` + `standard/profiles/<profile>.md` + `standard/repo.env`. If the
      rules changed, the sources were edited and the file **regenerated and committed** —
      never the other way round. A hand-edit to `CLAUDE.md` dies at the next regeneration and
      never reaches the other repos.
- [ ] **CI is green** — quality, security and functional. Not "green except for the flaky one".
