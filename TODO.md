# TODO

Single list of **open** work (statuses ⬜/🟡). Done tasks (✅) move to
[CHANGELOG.md](CHANGELOG.md) — see the rule below.

## Current state / next action

On `feature/PRJ-1-multi-repo-standard`. The standard is now **generated**: `standard/base.md`
plus one of four profiles, composed by `standard/compose.sh` into `CLAUDE.md`, with
`templates/<profile>/` carrying the scaffold for each. This is being field-tested by the
`job-agent` group, which is where the requirements come from.

**Next action: PRJ-2** — the standard asserts three enforcement mechanisms and none of them
exists. Until the drift gate runs, nothing stops a repo's `CLAUDE.md` from silently diverging
from its sources, which is the whole point of generating it.

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
| PRJ-2 | ⬜ | **Make the enforcement mechanisms real** — `JAP-8` | The standard claims three gates and has none. (a) **`standard-drift`**: no CI job anywhere runs `compose.sh --check`, so the generated file can diverge from its sources undetected. (b) **`doc-sync`**: GitHub-only, and its code regex `^(src/\|chart/\|Dockerfile\|docker-compose\|\.github/workflows/)` misses `standard/`, `deploy/`, `helm/`, `.gitlab-ci.yml` and `skills/` — a change rewriting the entire standard passes it untouched; its docs regex misses `AUTOPILOT-LOG.md`. (c) the mandated log format is unenforced. |
| PRJ-3 | ⬜ | **`docs/contracts.md` is required but absent** | The context map, the doc-sync table and lifecycle step 4 all reference it. It exists in `templates/*/docs/` but not at the repo root. |
| PRJ-4 | ⬜ | **`scripts/check-versions.py` is called but absent** | Both version-audit skills open with `./scripts/check-versions.py`, and so does the *Keeping deployed versions current* section. `scripts/` does not exist here. It is written in `job-agent/infra/dev-stack` — port it, do not rewrite it. |
| PRJ-5 | ⬜ | **This repo violates its own `service` profile** | Layout is `Dockerfile` + `chart/`; the profile declares `deploy/Dockerfile` + `helm/` canonical and requires a deviation note in `docs/architecture.md`. Either migrate the layout or write the note — silence is the one option the profile excludes. |
| PRJ-6 | ⬜ | **Docs contradict the standard they ship** | `docs/tests.md` lists three tiers where the standard defines four, and says "GitHub Actions CI" although GitLab is the required platform. `docs/architecture.md` says "Container image (GHCR) → Helm chart (`chart/`)" and its decision log has no entry for the profile model. `docs/configuration.md` is GitHub-only (`gh variable set`, environment `ci-functional`). |
| PRJ-7 | ⬜ | **GitLab parity** — `JAP-11` | `CODEOWNERS` in GitLab syntax + approval rules; `renovate.json` replacing Dependabot; `.gitlab/merge_request_templates/default.md`; a GitLab publish job; documented `glab` commands for protecting `dev`/`rc`/`release`. |
| PRJ-8 | ⬜ | **Observability as part of "done"** — `JAP-12` | Metrics, structured JSON logging with Loki structured metadata, a dashboard updated in the same change, `docs/observability.md`. Extends the doc-sync table, the per-task lifecycle and the `service` profile; makes a metrics and a log backend hard requirements. |
| PRJ-9 | ⬜ | **Stale references in the shipped files** | `.claude/settings.json` hooks list a context map that predates `docs/contracts.md`, `AUTOPILOT-LOG.md` and `standard/`. `.gitlab-ci.yml` sets `FUNCTIONAL_PORT`/`FUNCTIONAL_PATH`, which `functional.yml` never reads (it discovers `auto-tests/group-a/*.sh` via `FUNCTIONAL_TESTS_DIR`/`GLOB`, both defaulted in `globals.yml`) while the script itself reads `APP_PORT`; its header comment cites a `/standard.yml` include that does not exist. `README.md` references a non-existent `docker-compose.voice.yml`. `chart/values.yaml` claims "no GatewayAPI coupling" while shipping an `HTTPRoute`. `.claude-plugin/*.json` hardcode `version: 0.1.0` against the never-hardcode-a-version rule. |
| PRJ-10 | ⬜ | **No coverage threshold** | `pytest-cov` is installed and never configured — no `--cov-fail-under`, no `[tool.coverage]`. Each repo will drift on the quality bar the standard claims to set. |
| PRJ-11 | 🟡 | **Delete Ansible from `templates/infra/`** — `JAP-20` | User decision 2026-07-27. To delete: `ansible.cfg`, `.ansible-lint`, `inventories/laptop-local/{hosts.yml,group_vars/all.yml}`, `playbooks/site.yml`, `roles/requirements.yml`, `collections/requirements.yml`, and the `ansible-lint` + `ansible-playbook --syntax-check` job in `.gitlab-ci.yml`; plus every Ansible sentence in `README.md` and `docs/`. Replace with the shape the profile describes and the group uses: a Flux/kustomize tree (`clusters/<cluster>/`, `apps/<component>/{ks.yml,app/}`, `repositories/`), linted with `yamllint` + `kubeconform` + `flux build`. Note the profile text in `standard/profiles/infra.md` is already tool-agnostic — only its CI paragraph names a provisioning tool. **`kk_private/k8s-laptop` keeps Ansible** (user decision) — it is outside this standard's scope and is what builds the cluster. |
| PRJ-12 | 🟡 | **Strip this-project specifics out of the standard** | User decision 2026-07-27: *"это template standard — там не должно быть никакой специфики от этого проекта, там только подходы"*. Contamination found: `standard/base.md` uses `JAP-<n>` as the platform-id example and `apply-dispatch`/`DISP-3` as the worked row; `standard/profiles/platform.md` ships a bundle example naming `job-agent-dev`, `registry.gitlab.com/job-agent` and `redpanda`; `standard/profiles/service.md` hardcodes `open_ci_cd/templates`, `korkin25/open-ci-actions@v1` and `oci://registry.gitlab.com/job-agent/charts/`; `repo.env.example` and `compose.sh` use `job-agent-shared` as the worked example. In `templates/`: `platform/requirements.yaml` (8 references), `platform/clusters/laptop-local/environments/dev/bundle.yaml` (5), and job-agent names across every profile's `.gitlab-ci.yml`, `TODO.md` and `repo.env`. Every example must be a neutral placeholder; the standard teaches the approach and the consuming group supplies the names. |

| PRJ-13 | ⬜ | **Observability is part of the definition of done** — `JAP-12` | User requirement 2026-07-27, stated as non-negotiable: a feature ships **with** its metrics, not after. Into `standard/base.md` (binds every profile) and the `service` profile: (a) Prometheus metrics for the feature's own behaviour, not just RED on the endpoint; (b) structured JSON logging, one schema across every service, from the shared library so no service invents its own; (c) every field as **Loki structured metadata**, never packed into the message body — a field you regex out of a log line is not queryable; (d) **the Grafana dashboard updated in the same change**, ideally generated from the metric definitions rather than hand-drawn, because a hand-drawn panel is the first thing to rot; (e) `docs/observability.md` documenting each metric, what value is bad and what to do about it. Extends the doc-sync table and the per-task lifecycle. Makes a metrics backend and a log backend hard `requirements.yaml` entries. |
| PRJ-14 | ⬜ | **The standard must be host-agnostic; I made it GitLab-mandatory** | User correction 2026-07-27: the standard is the general case and carries examples for **both** GitLab and GitHub; the concrete project's devops picks one. My earlier edit to `standard/profiles/service.md` wrote "GitLab is the only platform a repo is required to support" and demoted GitHub to optional — that is a *project* decision (job-agent is on GitLab) that leaked into the standard. Rewrite as: one hosting platform per project, chosen once and recorded in the project's `docs/architecture.md`; the standard shows the mapping for both (`.gitlab-ci.yml` include-composition ↔ `.github/workflows` reusable-workflow composition; container registry ↔ registry; package registry ↔ registry; MR template ↔ PR template; `CODEOWNERS` syntax; Renovate ↔ Dependabot) and takes no side. |
| PRJ-15 | ⬜ | **Helm chart standardization is a first-class part of the standard** | Listed by the user among the standard's required subjects. Today it is a section of the `service` profile; verify it actually covers what a fleet needs — probes, security context, resources, `envFrom` conventions, `ServiceMonitor`, routing via Gateway API, secret references, and the CI-written version/tag fields — and that nothing in it is project-specific. |

| PRJ-16 | ⬜ | **Prove the demo service still builds — on GitHub** | The last four CI runs on this branch were green (≤1m18s), but they predate today's work: the standard rewrite, the four profiles, the `templates/` tree and the `templates/infra` de-Ansible are all **uncommitted**. Commit, push, read the run logs even when green, and fix whatever the chart/image/functional jobs surface. Note `doc-sync` has only ever run on a pull request, never on a push — its behaviour on this change set is untested. |
| PRJ-17 | ⬜ | **Mirror the standard to GitLab and prove parity** | `korkin25/ai-project-template` does not exist on GitLab yet. Create it, push, and verify the `.gitlab-ci.yml` composition produces the same guarantees as the GitHub one: language gates, SAST, image, chart, functional. This is also the honest test of `PRJ-14` — a standard that claims to be host-agnostic but has only ever run on one host has not demonstrated anything. **Requires a runner** (`JAP-1`), and **nothing may be committed to the shared templates repo** to make this work — if a template change is needed, it is a request to the user, not an edit. |

## Planned / ideas

- **`ai-standard-plugin`** — distribute the skills and hooks as a plugin marketplace instead of
  copying `.claude/settings.json` into every repo: `new-repo`, `release-service`,
  `bump-bundle`, `sync-standard`, `cross-repo-status`, plus the two version-audit skills that
  currently live here. Tracked as `JAP-14` on the consuming side.
