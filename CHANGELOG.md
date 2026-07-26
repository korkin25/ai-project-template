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
- **`Status is half the record`** — a status is updated in the change that changes the
  reality, not in a later sweep. A logged task nobody re-touches produces a file that looks
  authoritative and is wrong, and the failure is specific: the work finishes, the code and the
  changelog are perfect, and every ticket still reads `⬜`, so the next session re-derives what
  was already done or redoes it.
- **`GET /metrics` is registered as a contract in the `service` scaffold** (`PRJ-20`).
  `templates/service/docs/contracts.md` listed `/health` and not `/metrics`, while the
  scaffold served the endpoint, the chart scraped it through a `ServiceMonitor` and the
  tier-(a) script probed it — so the one file a consumer reads *instead of* the source omitted
  the endpoint an operator's Prometheus actually depends on. The row records the response
  shape and the exposition `Content-Type`; the metric names are deliberately not pinned,
  because adding a series is additive while the endpoint, its port and its format are what
  anyone builds on.
- **Tier-(a) tests for `/metrics` in the `service` scaffold** (`PRJ-21`), three of them: the
  endpoint answers `200` with the exposition `Content-Type` and a body carrying a `# TYPE`
  line; `/health` and `/metrics` report one version; and the counters move with the worker.
  Asserted over HTTP on an ephemeral port rather than against the renderer, because the header
  a scraper depends on comes from the handler — a renderer-only test stays green while the
  endpoint answers with something Prometheus marks UP and stores nothing from. Shape, never an
  exact payload: the reasoning is copied from `auto-tests/group-a/validate-deploy.sh`, which
  already asserts the same invariant one level up.

### Fixed

- **The three advertised enforcement mechanisms now exist** (`PRJ-2`). `standard-drift`
  regenerates `CLAUDE.md` and fails on any difference, distinguishing a drifted file from a
  broken `repo.env` because the fix differs. `doc-sync` gained the GitLab half it never had,
  and its code regex — which missed `standard/`, so a change rewriting the entire rulebook
  passed the gate untouched — now covers the real surface on both hosts, byte-identically.
  Both gates also ship in the `service`, `library` and `infra` scaffolds, so a spawned repo
  gets the enforcement its generated `CLAUDE.md` promises.
- **`docs/contracts.md`** (`PRJ-3`) — required by the context map, the doc-sync table and
  lifecycle step 4, and absent from the repo that mandates it.
- **The version-audit skills are runnable** (`PRJ-4`). Both opened with
  `./scripts/check-versions.py`, which does not exist here. A root copy was rejected on
  evidence rather than added: run against this repo the ported reader returns one row, a
  documented placeholder, while seeing none of the real pins — which already have an owner in
  `dependabot.yml`. The skills now state the per-repo convention and carry a manual fallback.
- **The `infra` profile is a GitOps tree, not an Ansible repo** (`PRJ-11`), structurally and
  in every line of its prose.
- **No project-specific names left in the standard or the scaffolds** (`PRJ-12`, `PRJ-14`).
  The host-agnostic rewrite also reverted an earlier mistake: "GitLab is the only platform a
  repo is required to support" is a project decision that had leaked upstream.

- **The repo's own docs no longer contradict the standard they ship** (`PRJ-6`).
  `docs/tests.md` described three test tiers where the standard defines four, and pinned tier
  (a) to one CI host — a tier is defined by *CI runs it unattended*, never by which host.
  `docs/architecture.md` gained `PRJ-D1`, the ADR for generating `CLAUDE.md` from `standard/`,
  including why a shared file by URL or submodule was rejected: every agent runtime picks
  rules up **by name at the repo root**, so the content has to physically be there, and a
  submodule is unreadable in a shallow clone or an offline sandbox. It also now records the
  layout deviation the `service` profile permits only when written down, and that the CI-host
  choice is unsettled. `docs/configuration.md` is host-agnostic, with the one difference that
  actually bites: GitHub secrets are a separate write-only store, while GitLab has one store
  where **masking is opt-in** — an unmasked secret is a normal variable that gets echoed the
  first time something prints the environment, and the log that leaked it is not
  retroactively redacted.
- **Stale references removed** (`PRJ-9`). The per-turn hooks recited a context map predating
  `docs/contracts.md`, `AUTOPILOT-LOG.md` and `standard/`. `README.md` referenced a
  `docker-compose.voice.yml` and a model PVC inherited from the project this template was
  extracted from. `chart/values.yaml` claimed no Gateway-API coupling while templating
  `gateway.networking.k8s.io/v1`; the claim now separates what the chart never couples to from
  the opt-in CRD-backed resources that are absent-not-degraded when off and a cluster
  prerequisite when on — a release templating a kind whose CRD is missing fails at apply time,
  not lint time.
- **Both plugin manifests stopped declaring a version** (`PRJ-9`). This was not only a breach
  of never-hardcode-a-version: a pinned version means users receive an update *only* when the
  string is bumped, so every install was frozen at `0.1.0` forever. The field is optional and
  resolution falls back to the commit SHA, which is strictly better. Recorded in
  `docs/contracts.md` so re-adding it — the natural instinct — is recognisable as the bug.

- **A coverage floor that means something** (`PRJ-10`). It could not be set honestly before:
  coverage sat at 47% with `cli.py` entirely untested, so any passing value would have been
  one chosen to accommodate the hole. Tests first — `cli.py` 0% → 100%, total 47% → 83% with
  branch coverage on — then the gate at 80, a ratchet just under the current number whose only
  direction is up. Verified both ways: exit 0 at 80, exit 1 at 95.
- **`templates/platform/` became a usable scaffold** (`PRJ-18`). It shipped eight files and no
  `standard/repo.env`, so `compose.sh` could not run and a spawned platform repo had no
  `CLAUDE.md` at all — the drift gate would guard nothing and doc-sync would have no doc side.
  Eighteen files added, including the pipeline the profile describes and an `e2e/` directory,
  because every other profile says tier (d) lives here and a test with no home lands in a
  service repo instead. Verified by simulating adoption end to end.
- **The canonical layout** (`PRJ-5`) — `deploy/Dockerfile` and `helm/`, which deleted both CI
  overrides since the canon is what the shared templates already default to.
- **The `service` chart no longer names a registry** (`PRJ-22`). `templates/service/helm/values.yaml`
  shipped `registry.gitlab.com/@@GROUP@@/@@PROJECT@@` and an `imagePullSecrets[0].name` of
  `gitlab-registry` — one host hardcoded into a scaffold the standard requires to be
  host-agnostic, and inherited unchanged by every repo spawned from it. Both are now
  `@@REGISTRY@@` and `@@PULL_SECRET@@`, using the scaffold-instantiation mechanism already
  documented next to `@@CI_TEMPLATES_PROJECT@@`, `@@CI_TEMPLATES_REF@@` and `@@RUNNER_TAG@@`:
  tokens that live only under `templates/`, are substituted by whoever creates the repo, and
  are caught by that scaffold's own `grep -rnE '@{2}' .` gate. Neither became a `repo.env`
  key, deliberately — `compose.sh` writes `CLAUDE.md` and nothing else, so the key would be
  read by nobody while implying the generator resolves it, and a new required key breaks every
  existing `repo.env` at once. Both values are quoted, because `@` is a reserved YAML indicator
  and may not open a plain scalar. Verified by instantiating the scaffold twice, once per host:
  `helm lint` clean and `helm template` rendering `ghcr.io/…` with one pull secret and
  `registry.gitlab.com/…` with the other.

### Bookkeeping

- `PRJ-13` was a duplicate of `PRJ-8` (observability), created by logging the same requirement
  twice under two ids. Both are closed by the same change; `PRJ-8` is the surviving reference.
  Recorded rather than quietly deleted, because the ids are documented as never reused.

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
