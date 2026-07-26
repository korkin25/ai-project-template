# Changelog

All notable changes to @@PROJECT@@ are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

**This changelog is the deployment history of every environment.** It is read by other teams
and, more often, by whoever is trying to work out what changed shortly before something
started misbehaving. So every entry names **the environment, the component and the exact
version** — "bumped the service" is not an entry, it is a note to nobody.

There are no released versions here: this repo publishes no artifact, and what is "released"
is the state of an environment. Entries are grouped by the date the change was **observed in
the environment**, not by the merge date — merging starts the reconcile, and a reconcile can
fail. Until the state has been read back, the change stays in `TODO.md` under *Awaiting
reconciliation, or an approval*.

The rule that makes this file worth reading at 03:00: **a version bump entry says what it was
before**. A changelog that records only the new version cannot answer "what do I revert to",
which is the one question being asked of it.

## [Unreleased]

### Added

- Repository scaffolded from the shared `platform` template: validate-only GitLab CI pinned to
  `@@CI_TEMPLATES_PROJECT@@` at `@@CI_TEMPLATES_REF@@` (`yamllint`, `validate-bundles`,
  `render-diff`, a manual `e2e`, plus the `standard-drift` and `doc-sync` gates), one example
  cluster with a `dev` environment, `bundle.schema.json` with `additionalProperties: false`
  throughout, `requirements.yaml` as the contract with the infra repo, the three scripts, and
  the full doc set including `docs/environments.md`.

### Deployed

<!-- One row per environment change, newest first. State the before-version: it is what a
     rollback needs.
- `dev`: `<service>` 0.1.0 → 0.1.3 (@@PREFIX@@-14). Tier-(d) green, job 8123. Reverted by
  reverting !42. -->

### Changed

### Removed

<!-- Removing a component or an environment breaks consumers by definition. State what
     replaced it, which repos were affected, and the tickets opened in them. -->

### Fixed

### Security
