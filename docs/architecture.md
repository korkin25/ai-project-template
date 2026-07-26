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
is in [configuration.md](configuration.md); the chart's own knobs are in `chart/README.md`.

**CI host — not yet settled for this repo.** The standard requires exactly one host, chosen
once and recorded in this section. This repo currently carries *both* `.gitlab-ci.yml` and
`.github/workflows/ci.yml`, and only the GitHub one has ever run. That is the state the
standard warns about — a half-maintained second pipeline fails for reasons nobody
investigates and trains everyone to ignore a red check. Resolving it is `PRJ-14` (make the
standard host-agnostic) and `PRJ-17` (mirror to GitLab and prove parity); until one of them
lands, treat neither pipeline as authoritative.

### Layout deviation from the `service` profile

The profile declares `deploy/Dockerfile` and `helm/` canonical, because those are the shared
CI templates' defaults — a repo that uses them needs no `DOCKERFILE`/`CHART_PATH` override.
**This repo deviates: the image is built from the root `Dockerfile` and the chart lives in
`chart/`.** The reason is history, not design — the layout predates the profile, and this repo
is also the one every other repo is spawned from, so moving it is a change to the scaffolds
and the CI overrides in the same breath rather than a rename. The profile permits the
deviation only when it is written down, which is what this paragraph is; the cost is that this
repo must keep the two overrides its CI sets, and that a reader comparing it to
`templates/service/` sees two different layouts. Migrating to the canonical one is `PRJ-5`.

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
  than cosmetic — and it is **not yet wired into any CI** (`PRJ-2`). Until it is, this decision
  buys single-sourcing without the enforcement it assumes.
- Propagation is part of a rule change, not a follow-up. Between the upstream edit and the last
  repo's regeneration the group is running two standards and neither is authoritative.
- The generated header carries a `Sources-SHA256` over the *sources*, not the rendered output,
  so reformatting the generated file is caught as drift too.
- The four profile names, the mandated paths and the section headings become a cross-repo
  contract in their own right — renaming one breaks consumers that fail to compile nothing.
  They are registered in [contracts.md](contracts.md) for that reason.
