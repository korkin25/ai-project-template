# Changelog

All notable changes to @@PROJECT@@ are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

**This changelog is read by other teams**, because this repo's changes are the ones that
break everyone else's assumptions: a namespace that disappears, a runner tag that changes, a
storage class default that moves. So every entry says **what other repos must do** — usually
nothing, sometimes something specific.

There are no released versions here: this repo publishes no artifact, and what is "deployed"
is the state of the cluster. Entries are therefore grouped by the date the change was
**applied**, not by a version number — a merged-but-unapplied change stays in `TODO.md`
under *Awaiting a human apply*.

## [Unreleased]

### Added

- Repository scaffolded from the shared `infra` template: lint/validate-only GitLab CI
  pinned to a tagged `open_ci_cd/templates`, Ansible layout with exactly pinned collections
  and roles, `manifests/` for cluster prerequisites, and the full doc set including
  `docs/runbook.md`.

### Changed

### Removed

<!-- A removal here breaks consumers by definition. State the replacement, the repos
affected, and the tickets opened in them — e.g.
- Removed the `legacy-registry` pull secret. Replaced by `gitlab-registry` (added 2026-06-01).
  Consumers: SVC-3, SVC-9 — both migrated before the removal. -->

### Fixed

### Security
