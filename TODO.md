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

**Next action: PRJ-15** — review the Helm section of the `service` profile now that the
layout question is settled and the chart lives where the profile says it does.

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
| PRJ-7 | ⬜ | **GitLab parity** — `JAP-11` | `CODEOWNERS` in GitLab syntax + approval rules; `renovate.json` replacing Dependabot; `.gitlab/merge_request_templates/default.md`; a GitLab publish job; documented `glab` commands for protecting `dev`/`rc`/`release`. |
| PRJ-15 | ⬜ | **Helm chart standardization is a first-class part of the standard** | Listed by the user among the standard's required subjects. Today it is a section of the `service` profile; verify it actually covers what a fleet needs — probes, security context, resources, `envFrom` conventions, `ServiceMonitor`, routing via Gateway API, secret references, and the CI-written version/tag fields — and that nothing in it is project-specific. |
| PRJ-19 | 🟡 | **Every patch must be universal across GitHub and GitLab** | User rule 2026-07-27: this repo lives on both as **identical copies** — GitHub is the source, GitLab a mirror of it. That is the standard's one permitted exception to "support exactly one host", and it has already earned its keep: the functional probe passed on GitHub for months and could never have passed on GitLab, which only running it there revealed. Consequence: no change may touch one host's governance artefact without the other. Recorded in `docs/architecture.md` and in the `service` profile. Open part: audit every remaining GitHub-only assumption — `release.yml` is GitHub-only with no GitLab counterpart, and `docs/tests.md`/`README.md` may still name one host. |
| PRJ-23 | ⬜ | **The standard must say how services authenticate and authorize each other, and mandate default-deny network policy** — `JAP-34` | User request 2026-07-27. Today `base.md` covers secrets, least privilege and hostile inputs, and says **nothing about the network between services** — which in a multi-repo platform is the boundary that actually carries the traffic. Three coupled parts: transport identity (mTLS, or a CNI that provides it), an authorization model saying which service may call which, and **default-deny policy for every deployment**. They cannot be chosen independently: "only `matching` may call `apply`" is the same statement as a policy allowing that pair, and deciding them separately yields two half-enforced copies that disagree.<br><br>The scaffold consequence is what makes this the standard's problem rather than one project's: default-deny is only a boundary if it is the *default*, so the `service` profile's chart has to ship a policy and the platform has to ship the namespace baseline, together. **This also retires an existing waiver** — `CKV2_K8S_6` ("no NetworkPolicy") is skipped in `.checkov.yaml` here and in `dev-stack`, each with a written reason deferring to the infra repo. Those reasons stop being true when this lands, and removing them is part of the change. Worth generating policies from `docs/contracts.md` rather than hand-writing them: the dependency graph is already declared there, and a hand-maintained policy set rots the first time a topic moves. |
| PRJ-24 | ⬜ | **A rule for finding traffic that default-deny blocks and should not** — `JAP-35` | User request 2026-07-27, deliberately separate from PRJ-23 because it must be available **before** enforcement, not after. A missing allow-rule is invisible from both ends — the caller sees a timeout, the callee sees nothing — and that single failure mode is why teams roll default-deny back instead of finishing it.<br><br>The rule to write: **never enforce a policy that has not first run in audit mode.** Evaluate and record what *would* be denied while still allowing it, for a stated soak period, convert each verdict into an allow-rule or a deliberate denial, and only then enforce. Belongs beside *Observability*, because what makes it work is the same machinery: denied-flow verdicts as structured log fields, an alert with a named owner and an action, and a documented way to ask "what did this service fail to reach".<br><br>Verified on the reference cluster 2026-07-27 so the rule is written against something real, not imagined: Cilium has `enable-hubble: true` with `hubble-relay` and `hubble-ui` running, and `enable-policy: default` — meaning endpoints without a policy currently allow everything, which is exactly the starting state this rule addresses. `encryption-type` is **empty**: there is no transport encryption today, which is an input to PRJ-23's mTLS decision. Separately worth reporting upstream: `hubble-relay` shows **6438 restarts over 91 days**, so anything built on Hubble must tolerate it disappearing. |
| PRJ-31 | ⬜ | **`Functional` is red on every feature branch: it pulls an image the branch never published** | Diagnosed 2026-08-01 from the job's own artifact rather than from the log. `auto-tests/group-a/validate-deploy.sh` exits 1 after 7 s with:<br><br>`== using the image built by this pipeline: ghcr.io/korkin25/ai-project-template:0.1.0-alpha.1 ==`<br>`Error response from daemon: manifest unknown`<br><br>`Image / Build, scan & publish` passes, so docker works — the image is **built and not pushed** on a feature branch, while the functional job sets `IMAGE_REF` and pulls it unconditionally. Run the same script locally with `IMAGE_REF` unset and it builds `app:smoke` itself and passes in ~30 s, which is why this never surfaced outside CI.<br><br>**`dev` is green** (23 s, image genuinely published), so the red is a feature-branch artefact and disappears on merge — which is the trap: it trains everyone to merge past a red tick, and the next red one will be real.<br><br>Same class as job-agent `JAP-68`, seen from the opposite side: there `IMAGE_REF` is *unset* and the fallback build has no package index. Both come from one assumption — that the image the pipeline built is fetchable — being true only on publishing branches.<br><br>**Fix:** the script should fall back to building locally when the pull fails, exactly as it already does when `IMAGE_REF` is empty; or the job should not set `IMAGE_REF` on a branch that does not publish. The first is better — it keeps the test meaningful everywhere. |
| PRJ-17 | ⬜ | **Mirror the standard to GitLab and prove parity** | `korkin25/ai-project-template` does not exist on GitLab yet. Create it, push, and verify the `.gitlab-ci.yml` composition produces the same guarantees as the GitHub one: language gates, SAST, image, chart, functional. This is also the honest test of `PRJ-14` — a standard that claims to be host-agnostic but has only ever run on one host has not demonstrated anything. **Requires a runner** (`JAP-1`), and **nothing may be committed to the shared templates repo** to make this work — if a template change is needed, it is a request to the user, not an edit. |

## Planned / ideas

- **`ai-standard-plugin`** — distribute the skills and hooks as a plugin marketplace instead of
  copying `.claude/settings.json` into every repo: `new-repo`, `release-service`,
  `bump-bundle`, `sync-standard`, `cross-repo-status`, plus the two version-audit skills that
  currently live here. Tracked as `JAP-14` on the consuming side.
