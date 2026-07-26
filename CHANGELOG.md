# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **The standard is generated, not hand-maintained.** `standard/base.md` holds what binds
  every repository; `standard/profiles/{service,library,platform,infra}.md` hold what binds
  one kind; `standard/compose.sh` composes them with `standard/repo.env` into `CLAUDE.md`,
  stamping a checksum of the sources. `--check` regenerates and diffs, so a hand-edited
  `CLAUDE.md` is a detectable error rather than a silent divergence. The agent rule files
  (`AGENTS.md`, `GEMINI.md`, `.cursorrules`, …) remain symlinks to the generated file.
- **A multi-repo dimension**, because one standard now governs a group rather than a project:
  per-repo ticket prefixes with a platform id for cross-repo work; a contract registry
  (`docs/contracts.md`) and the protocol for changing a contract someone else consumes; the
  service↔platform interface reduced to one thing, the published version in `.versions/*.env`;
  a fourth test tier (d) for cross-service end-to-end, living in the platform repo; cross-repo
  blast-radius rules; and a mandatory `AUTOPILOT-LOG.md` with a fixed entry format.
- **Scaffolds for all four profiles** under `templates/`, including the platform profile's
  `bundle.schema.json`, a worked environment bundle, `validate-bundles.py`, `render.py` and
  `check-requirements.py` — the last of which verifies a live cluster against a declared
  `requirements.yaml` written in terms of capabilities rather than implementations.
- **Database schema changes are Liquibase changesets, always** — because a schema shared by
  several services is a cross-repo contract with no compiler to catch a rename.
- **A monthly version audit, as two skills** — `cluster-version-audit` for the substrate and
  `data-plane-version-audit` for anything holding state. Split deliberately: for the substrate
  a rollback is a chart version, while for stateful components the upgrade is frequently
  one-way and the backup comes first. Both report everything they find and apply nothing.
- **`Capture first`** — every request from the user is written into `TODO.md` immediately, in
  the turn it is asked, before answering or designing.
- **`Changing the rules — the standard is upstream`** — a new rule goes into `standard/` first
  and propagates down, never into a generated `CLAUDE.md`; propagation is part of the change;
  and this repository is the first consumer of every rule it publishes.

### Changed

- **Removed `Features.md` — features live in `README.md` `## Features`.** The user-facing
  feature list now lives in `README.md` under `## Features` (the Marketplace/PyPI/OpenVSX pages
  render the README, so that section is the feature list users see); backlog and not-yet-built
  ideas live in `TODO.md`. `Features.md` was deleted and every reference to it purged from the
  standard (`CLAUDE.md`, `.claude/settings.json`, `.cursor/rules/project.mdc`, PR/issue
  templates, `doc-sync.yml`, `CONTRIBUTING.md`). The "only user-facing features" scope rule was
  kept, now describing the README `## Features` section.
- **GitHub Releases on stable.** `release.yml` now, on a `release`-branch build, tags `vX.Y.Z` and cuts a GitHub Release (auto-notes + built artifacts). Pre-releases (`rc`) publish to the registry only (no tag), so pre-release tags never confuse GitVersion; the version stays driven by `next-version`. Doctrine updated in CLAUDE.md.

- **`Features.md` scoped to user-facing features only.** `CLAUDE.md` (Feature backlog) now
  states the backlog lists only user-facing product features; engineering/infra work
  (deployment, CI/CD, release, versioning, tooling, refactors, governance) is tracked in
  `TODO.md`/`CHANGELOG.md`, not the feature backlog. The template's own `Features.md` sample
  entries were replaced accordingly (health check + CLI) — the scaffold/CI entry moved out.
- **Release standard: no tags — a merge to `rc`/`release` publishes.** `release.yml` runs
  `on: push: branches: [rc, release]`: a merge to `rc` publishes a **pre-release** (PyPI
  `X.Y.ZrcN`), a merge to `release` publishes the **stable** `X.Y.Z`. The version comes entirely
  from **GitVersion** (single knob `next-version`; `rc` → `SemVer`, `release` →
  `MajorMinorPatch`), injected at build time (`hatch version`), never hardcoded — `pyproject.toml`
  is `dynamic = ["version"]`. Publishing is PyPI Trusted Publishing (vendored workflow; the
  reusable release job — removed from `ci.yml` — can't trusted-publish cross-repository).
  `GitVersion.yml` was rewritten to a clean **GitVersion 6.x-native** config (a 5.x-style config
  makes `next-version` fail to parse on GitVersion 6.8+). `CLAUDE.md` gained a "Versioning &
  releasing" doctrine (Python + VS Code-extension variants) and a rule to **quote failing CI log
  fragments** back to the user when diagnosing.
- **Tamed Dependabot + doc-sync exemption.** The `doc-sync` guard now skips dependency PRs
  (the `dependencies` label / `dependabot[bot]` actor) — a version bump carries no doc change.
  `dependabot.yml` opens **one grouped PR per ecosystem** and **ignores breaking major bumps**
  (minor/patch only; majors are a deliberate migration task). Prevents the dep-update swarm from
  going red out of the box.

### Added

- Initial template. Canonical rules in `CLAUDE.md`, picked up by every agent via symlinks
  (`AGENTS.md`, `GEMINI.md`, `.cursorrules`, `.clinerules`, `.windsurfrules`,
  `.github/copilot-instructions.md`) and a Cursor `.mdc` pointer. Rules cover: a router
  "context map" + per-turn reminder hook (`.claude/settings.json`) + a CI `doc-sync` guard so
  agents don't forget the docs/tests/skills; **design-before-code**; **safe-autonomy**
  (autonomous vs. approval-gated actions + guardrails); **agent-security working agreements**
  (prompt/tool-injection defenses, least privilege, supply-chain); the three-group testing
  policy; and the per-task lifecycle. Plus: numbered backlog (`Features.md`), `TODO.md`,
  `docs/` (architecture + configuration + test catalog), `auto-tests/` (group a/b/c). CI is a
  **composition** of the public reusable workflows in `korkin25/open-ci-actions@v1`
  (detect → python: ruff/mypy/pytest + radon-xenon → sast: gitleaks/semgrep/bandit/pip-audit/
  checkov/hadolint/trivy → docker → GHCR → helm → GHCR OCI → functional → release: PyPI),
  plus GitHub's default CodeQL code-scanning; the `.gitlab-ci.yml` mirror reuses `open_ci_cd/templates`
  (image → GitLab Container Registry, chart → Package Registry, same scanner set). The
  version is auto-generated by a shipped `GitVersion.yml` (branch model `feature/*` → `dev` →
  `rc` → `release`, **no `main`**) and shared by both CIs and the docs. Adds the Python gates,
  `Dockerfile` + `docker-compose.yml`, a generic Helm chart (Gateway API HTTPRoute), a portable `SKILL.md`
  template with `.claude-plugin/` manifests, `.pre-commit-config.yaml` (gitleaks via Docker),
  community files (LICENSE/CONTRIBUTING/SECURITY/CoC, CODEOWNERS, dependabot, issue/PR
  templates), and a tiny sample `app` service so the pipeline is green out of the box.
