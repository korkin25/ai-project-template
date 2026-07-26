# TODO

Single list of **open** work (statuses ⬜/🟡). Done tasks (✅) move to
[CHANGELOG.md](CHANGELOG.md) — see the rule below.

## Current state / next action

On `feature/PRJ-1-multi-repo-standard`. The standard is now **generated**: `standard/base.md`
plus one of four profiles, composed by `standard/compose.sh` into `CLAUDE.md`, with
`templates/<profile>/` carrying the scaffold for each. This is being field-tested by the
`job-agent` group, which is where the requirements come from.

The gates are live and proven: `standard-drift` runs green on GitHub in ~10s, and `doc-sync`
was verified by extracting its script and running it against stubbed diffs on every profile.
Both now ship in the `service`, `library` and `infra` scaffolds too.

**Next action: PRJ-5** — decide the layout question, because it is the one place this repo
still contradicts a rule it publishes, and `PRJ-15` (the Helm review) depends on the answer.

## Legend

⬜ Planned · 🟡 In progress · ✅ Done → moved to `CHANGELOG.md`

## Maintenance rule

- Every request from the user is written here **immediately**, in the turn it is asked, before
  any other work — see *Capture first* in [CLAUDE.md](CLAUDE.md).
- A rule the user asks for goes into `standard/` first, then propagates — see *Changing the
  rules*. This repo is the first consumer of every rule it publishes.
- As soon as a task becomes ✅, move its row from `TODO.md` into `CHANGELOG.md` under the
  matching `## [Unreleased]` subsection.
- Never mark a task ✅ without confirmation that it actually works (a passing test).

## Task IDs

Tasks use local identifiers `PRJ-<n>`, decisions `PRJ-D<n>`. Numbering is mandatory and IDs
are never reused. Work spanning several repositories additionally carries a platform id from
the consuming group (for `job-agent` that is `JAP-<n>`), cited in the row.

## Open tasks

| id | | Task | Details |
|---|---|---|---|
| PRJ-1 | 🟡 | **Multi-repo standard: generated `CLAUDE.md`, four profiles, scaffolds** | `standard/{base.md,profiles/*,compose.sh,repo.env}` + `templates/{service,library,platform,infra}/`. Adds the cross-repo dimension: contract ownership, the service↔platform interface, test tier (d), cross-repo blast radius, mandatory `AUTOPILOT-LOG.md`, Liquibase-always, the monthly version audit, *Capture first*, *Changing the rules*. Field-tested by `job-agent`. |
| PRJ-5 | ⬜ | **This repo violates its own `service` profile** | Layout is `Dockerfile` + `chart/`; the profile declares `deploy/Dockerfile` + `helm/` canonical and requires a deviation note in `docs/architecture.md`. Either migrate the layout or write the note — silence is the one option the profile excludes. |
| PRJ-6 | 🟡 | **Docs contradict the standard they ship** | `docs/tests.md` lists three tiers where the standard defines four, and says "GitHub Actions CI" although GitLab is the required platform. `docs/architecture.md` says "Container image (GHCR) → Helm chart (`chart/`)" and its decision log has no entry for the profile model. `docs/configuration.md` is GitHub-only (`gh variable set`, environment `ci-functional`). |
| PRJ-7 | ⬜ | **GitLab parity** — `JAP-11` | `CODEOWNERS` in GitLab syntax + approval rules; `renovate.json` replacing Dependabot; `.gitlab/merge_request_templates/default.md`; a GitLab publish job; documented `glab` commands for protecting `dev`/`rc`/`release`. |
| PRJ-9 | 🟡 | **Stale references in the shipped files** | `.claude/settings.json` hooks list a context map that predates `docs/contracts.md`, `AUTOPILOT-LOG.md` and `standard/`. `.gitlab-ci.yml` sets `FUNCTIONAL_PORT`/`FUNCTIONAL_PATH`, which `functional.yml` never reads (it discovers `auto-tests/group-a/*.sh` via `FUNCTIONAL_TESTS_DIR`/`GLOB`, both defaulted in `globals.yml`) while the script itself reads `APP_PORT`; its header comment cites a `/standard.yml` include that does not exist. `README.md` references a non-existent `docker-compose.voice.yml`. `chart/values.yaml` claims "no GatewayAPI coupling" while shipping an `HTTPRoute`. `.claude-plugin/*.json` hardcode `version: 0.1.0` against the never-hardcode-a-version rule. |
| PRJ-10 | 🟡 | **No coverage threshold** | `pytest-cov` is installed and never configured — no `--cov-fail-under`, no `[tool.coverage]`. Each repo will drift on the quality bar the standard claims to set. |
| PRJ-15 | ⬜ | **Helm chart standardization is a first-class part of the standard** | Listed by the user among the standard's required subjects. Today it is a section of the `service` profile; verify it actually covers what a fleet needs — probes, security context, resources, `envFrom` conventions, `ServiceMonitor`, routing via Gateway API, secret references, and the CI-written version/tag fields — and that nothing in it is project-specific. |
| PRJ-17 | ⬜ | **Mirror the standard to GitLab and prove parity** | `korkin25/ai-project-template` does not exist on GitLab yet. Create it, push, and verify the `.gitlab-ci.yml` composition produces the same guarantees as the GitHub one: language gates, SAST, image, chart, functional. This is also the honest test of `PRJ-14` — a standard that claims to be host-agnostic but has only ever run on one host has not demonstrated anything. **Requires a runner** (`JAP-1`), and **nothing may be committed to the shared templates repo** to make this work — if a template change is needed, it is a request to the user, not an edit. |
| PRJ-18 | 🟡 | **`templates/platform/` is not a usable scaffold** | It ships eight files — `bundle.schema.json`, `requirements.yaml`, three scripts and one example bundle — and none of the repo skeleton every other profile carries: no `standard/repo.env`, so `compose.sh` **cannot run** and a spawned platform repo has no `CLAUDE.md` at all; no `README.md`, `TODO.md`, `CHANGELOG.md`, `AUTOPILOT-LOG.md`, `docs/*`; no `.gitlab-ci.yml`, so no `validate-bundles`, no `render-diff`, and neither enforcement gate. `docs/contracts.md` states every profile carries that skeleton, so the contract is currently false for one of the four. Adding the gates there is meaningless until the scaffold exists — completing it is the prerequisite. |
## Planned / ideas

- **`ai-standard-plugin`** — distribute the skills and hooks as a plugin marketplace instead of
  copying `.claude/settings.json` into every repo: `new-repo`, `release-service`,
  `bump-bundle`, `sync-standard`, `cross-repo-status`, plus the two version-audit skills that
  currently live here. Tracked as `JAP-14` on the consuming side.
