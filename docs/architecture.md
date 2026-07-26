# Architecture

> **Design-before-code lives here.** Per `CLAUDE.md`, no implementation starts until the
> design for a task is written down (data model, public API/contract, deployment shape,
> trade-offs vs. alternatives) and any architectural decision is approved. Record each such
> design in this file (or the ticket) before coding.

## Overview

<Describe what the system is and its main components in a few sentences.>

## Components

| Component | Responsibility |
|-----------|----------------|
| `src/app/` | <the service> |
| … | … |

## Data model

<The source of record, storage, schema, and what is derived/rebuildable.>

## Public interfaces / contracts

<CLI commands, HTTP/MCP API surface, event formats — the things other systems depend on.>

## Deployment shape

**Container image → Helm chart, both published at the same `GitVersion_SemVer`.** The standard
names no registry: the image and the chart go to whichever registry the chosen CI host already
provides, and to the *same* one — a second registry is a second set of credentials, a second
retention policy and a second thing to be out of sync. Which host and therefore which registry
is a project decision recorded here, not something the standard decides. Runtime configuration
is in [configuration.md](configuration.md); the chart's own knobs are in `helm/README.md`.

**CI host — settled: GitHub is the source, GitLab is a mirror, and both run the gates.**
`github.com/korkin25/ai-project-template` is where changes land;
`gitlab.com/korkin25/ai-project-template` is a mirror of it. They are **identical copies** —
not two repositories that happen to agree, which is the state the standard warns about, but
one repository reachable from two places.

**Therefore every change here must be universal.** No patch may assume a host. The governance
artifacts exist in both dialects and are edited in the same change — `.github/CODEOWNERS` and
`.gitlab/CODEOWNERS`, `dependabot.yml` and `renovate.json`,
`PULL_REQUEST_TEMPLATE.md` and `merge_request_templates/default.md`, `ci.yml` and
`.gitlab-ci.yml`. Updating one side and leaving the other is incomplete work: it teaches
readers that the review bar depends on which host they happened to open.

This is the one profile-level exception the standard permits, and it is permitted for a
reason it has already earned. `auto-tests/group-a/validate-deploy.sh` passed on GitHub for
months and **could never have passed on GitLab** — it probed `localhost` after publishing a
port into a DinD service's network namespace, which is reachable only as `docker`. Running
the same committed script on the second host is what found it, and every repo scaffolded from
here had inherited the same defect. A mirror that runs only a decorative subset would have
found nothing.

Where a capability exists on one host only, it is recorded here rather than left for someone
to discover from a red pipeline. Known today: PyPI Trusted Publishing via OIDC works from
both, but only for public PyPI — GitLab's own package registry authenticates with
`CI_JOB_TOKEN` and has no OIDC path.

### Layout — canonical, and deliberately so

`deploy/Dockerfile` and `helm/`, which is what the `service` profile declares and what the
shared CI templates already default to. The repo previously used a root `Dockerfile` and
`chart/`, inherited from before the profile existed, and carried two `DOCKERFILE`/`CHART_PATH`
overrides to compensate.

Both overrides are now gone, and that is the concrete argument for having migrated rather than
documenting the deviation: **the canonical layout costs nothing and the deviation cost two
lines of configuration that only restated a default.** Every override is a line a reader must
check against upstream before trusting it.

The other reason is precedent. This repository is the first consumer of every rule it
publishes, and the rule that a deviation must be written down exists for repos with a real
constraint — not as a way for the standard's own repo to exempt itself from its own canon
while telling eleven others to follow it.

## Decisions log

Record architectural decisions as `PRJ-D<n>` (short ADR-style entries): context → options →
decision → consequences.

### PRJ-D1 — `CLAUDE.md` is generated from `standard/` + a profile

**Context.** The rulebook is consumed by a dozen repositories, and until this branch each one
carried its own hand-written `CLAUDE.md`. That does not scale in the way that matters: a rule
added in one repo is not a rule, it is a local habit, and nothing tells the other eleven it
exists. Repos also differ in kind — a deployable service, a published library, the platform
that integrates them, the infrastructure underneath — so a single flat file is either too
vague to bind anyone or full of clauses most repos must ignore.

**Options considered.**

1. *Keep one hand-written `CLAUDE.md` per repo.* Zero tooling; the status quo. Rejected: it
   has no propagation mechanism at all, and divergence is invisible — nothing fails when two
   repos disagree about what "done" means.
2. *One shared file referenced by URL or a git submodule.* Genuinely single-source. Rejected
   for how agents actually load rules: every runtime picks the file up **by name at the repo
   root** (`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, …), so the content must physically exist
   there. A submodule additionally makes the rulebook unreadable in a shallow clone or an
   offline sandbox, and a URL makes it unreadable exactly when the network is the problem.
3. *Compose the file per repo from shared sources.* `standard/base.md` (binds every profile) +
   `standard/profiles/<profile>.md` (binds one kind of repo), rendered by `standard/compose.sh`
   with values from `standard/repo.env`, output committed at the repo root.

**Decision.** Option 3. Four profiles — `service`, `library`, `platform`, `infra`. `repo.env`
supplies seven `@@…@@` placeholders and the generator hard-fails on any that survives, so a
missed substitution is a build error rather than a rulebook telling agents to read
`@@PROJECT@@`. The generated file is committed, not gitignored, because the agents that need
it never run the generator. `compose.sh --check` re-renders in memory and diffs, and its exit
codes are distinct (`0` ok · `1` config error · `2` drift) so a gate can tell "the committed
file is stale" from "`repo.env` is broken" — two findings with opposite remedies. `repo.env`
is *parsed, never sourced*: it is committed configuration, and config that can execute shell
is a supply-chain hole in the standard's own tooling.

**Consequences.**

- Editing `CLAUDE.md` directly is now a **bug**: the change is erased on the next
  regeneration and never reaches the other repos. The rule sources are the only place to write.
- One rule edit propagates by construction — but only to repos that actually regenerate.
- The standard is **vendored, not referenced**. There is no version pin for a consumer to bump
  and nothing announces a new version, so a stale copy is silent until someone regenerates.
  The drift gate is the only thing that catches it, which makes that gate load-bearing rather
  than cosmetic. It is now wired on both hosts and in the `service`, `library`, `infra` and
  `platform` scaffolds (`PRJ-2`), so a repo created from here inherits the enforcement rather
  than the promise of it. Note what the gate can and cannot see: it proves a repo's committed
  `CLAUDE.md` matches *its own* vendored sources — it cannot tell that those sources are a
  version behind upstream. Catching that is the `sync-standard` skill's job, and it does not
  exist yet.
- Propagation is part of a rule change, not a follow-up. Between the upstream edit and the last
  repo's regeneration the group is running two standards and neither is authoritative.
- The generated header carries a `Sources-SHA256` over the *sources*, not the rendered output,
  so reformatting the generated file is caught as drift too.
- The four profile names, the mandated paths and the section headings become a cross-repo
  contract in their own right — renaming one breaks consumers that fail to compile nothing.
  They are registered in [contracts.md](contracts.md) for that reason.
