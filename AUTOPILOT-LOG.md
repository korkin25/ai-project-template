# Autopilot log — ai-project-template

Autonomous changes (user authorized publishing this repo + full autopilot on the CI chain).

Entries are **newest first**, in the format this repo's own standard mandates.

## 2026-07-27 — two rules about how rules themselves work

**What changed.** Two sections added to `standard/base.md`, and `CLAUDE.md` regenerated:

- ***Capture first*** — every request from the user is written into `TODO.md` immediately, in
  the turn it is asked, before answering or designing. Logged even when about to be done,
  even when unclear, even when disagreed with. Multi-part requests become multiple rows;
  cross-repo requests get a platform id plus a local row in each acting repo.
- ***Changing the rules — the standard is upstream*** — a new rule goes into `standard/`
  first and propagates down, never straight into a project's generated `CLAUDE.md`. Includes
  the test for what is a rule versus what is architecture ("would a brand-new, unrelated
  project need this?"), the statement that propagation is part of the change rather than a
  follow-up, and the requirement that this repository obeys every rule it publishes.

**Also:** `TODO.md` rewritten from the pristine template into real work — `PRJ-1` (this
branch, retroactively logged) through `PRJ-10`, several of them findings that this repository
fails its own standard.

**Why.** The user stated the second rule directly: this template is what future services are
spawned from, so a rule added only to the project being built is a rule the next project will
not have. The first rule earns its place empirically — three requests earlier in the same
session (the GPU check, the codebase-RAG brainstorm, the MCP recommendations) survived only
because the user re-raised them. A rule that depends on an agent remembering is not a rule.

**Verified by.** `./standard/compose.sh` → `wrote CLAUDE.md (profile=service)`;
`./standard/compose.sh --check` → `OK: CLAUDE.md matches standard/`. `grep 'Capture first'
CLAUDE.md` → present. Not verified: nothing ran in CI — there is no runner (see *Open*).

**Reverse.** Revert the two sections in `standard/base.md`, re-run `./standard/compose.sh`,
and restore `TODO.md` from git history.

**Open.** Five commits sit on `feature/PRJ-1-multi-repo-standard` and **none of them was ever
verified by CI** — the `job-agent` group's only runner was deregistered before its replacement
existed, so no pipeline has run. Everything here is verified locally only. The rules added
today assert enforcement (`standard-drift`, `doc-sync`) that **does not exist yet** — `PRJ-2`,
and it is the reason `PRJ-2` is the next action rather than a cleanup item. The copy of
`standard/base.md` vendored in `job-agent/infra/dev-stack` is 59 diff-lines behind and must be
regenerated; propagation is not finished until it is.

## 2026-07-26 — adopt open-ci-actions + publish

- **CI is now a composition of `korkin25/open-ci-actions@v1`** (detect → version → python /
  sast / docker / helm / functional / release), replacing the inline jobs. `.github/workflows/ci.yml`
  is the canonical reference composition (copy-paste for new projects). CodeQL + doc-sync stay
  as bespoke extra workflows. _Reverse:_ restore the previous inline `ci.yml` from git history.
- **Functional script slimmed** to image boot + `/health` probe (chart lint is the shared
  `helm` job now). Contract exit 0/77/other.
- **Published as a PUBLIC repo, default branch `dev`** (branch model feature/* → dev → rc →
  release; no main). This is the reference implementation every other project is aligned to.
- Docs kept in lockstep (CLAUDE.md Build/CI section, README, CHANGELOG).

## 2026-07-26 — CI debugging (open-ci-actions v1.0.2)

- **Removed `.github/workflows/codeql.yml`.** On a fresh public repo GitHub auto-enables
  CodeQL *default setup*, which conflicts with an advanced CodeQL workflow → 0s
  startup_failure ("workflow file issue"). CodeQL still runs via GitHub's default setup
  (Security → Code scanning), no workflow file needed. If a bespoke CodeQL config is wanted
  later, add it to open-ci-actions' `sast.yml`, not as a per-repo workflow. Docs updated.
- **Upstream fix in open-ci-actions v1.0.2:** checkov's SARIF `--output-file-path` must name
  a file, not a directory (checkov 3.x IsADirectoryError → no report → hard fail). Fixed in
  `sast.yml`; this repo picks it up via `@v1`.
- Pipeline result before these fixes: 15/16 green (checkov the only failure) + functional
  (script-driven) green — proving the composition works end to end on the demo app.
