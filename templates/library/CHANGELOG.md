# Changelog

All notable changes to @@PROJECT@@ are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) — with the version
itself computed by GitVersion, never written by hand.

**For a library this file is read by other teams**, not only by this repo's maintainers: it
is how a consumer decides whether a bump is safe. So every entry that touches the public API
says explicitly what a consumer must do — nothing, or something specific. `Deprecated` and
`Removed` are not optional sections here; they are the migration plan.

Entries land here when a task is done and verified, moved out of `TODO.md` in the same
change.

## [Unreleased]

### Added

- Repository scaffolded from the shared `library` template: composition-only GitLab CI
  pinned to a tagged `open_ci_cd/templates`, branch-gated publish to the group PyPI
  registry, an enforced exported-symbol registry (`docs/contracts.md` + the test that fails
  when the two disagree), and the full doc set.
- `Envelope`, `new_envelope` — the shared message envelope. See `docs/contracts.md`.

### Changed

### Deprecated

<!-- Deprecations state the replacement AND the version that removes the old symbol, e.g.
- `old_name` — deprecated since 0.3, removed in 1.0. Use `new_name`; the argument order is
  unchanged. -->

### Removed

### Fixed

### Security
