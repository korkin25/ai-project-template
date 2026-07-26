# Autopilot log — ai-project-template

Autonomous changes (user authorized publishing this repo + full autopilot on the CI chain).

Entries are **newest first**, in the format this repo's own standard mandates.

## 2026-07-27 — three owed follow-ups in the `service` scaffold

**What changed.** Three defects in `templates/service/`, each one inherited by every repo
spawned from it:

- **`docs/contracts.md` (`PRJ-20`)** — `/metrics` added to the HTTP table. The scaffold served
  the endpoint, `helm/templates/servicemonitor.yaml` scraped it and the tier-(a) script probed
  it, while the registry a consumer reads *instead of* the source listed only `/health`.
- **`tests/test_main.py` (`PRJ-21`)** — three tier-(a) tests for `/metrics`: `200` plus the
  exposition `Content-Type` plus a `# TYPE` line; one version across `/health` and `/metrics`;
  counters that move with the worker. `docs/tests.md` baseline table updated to match, and its
  `validate-deploy.sh` row corrected — the script has probed `/metrics` for some time and the
  row still said `/health` only.
- **`helm/values.yaml` (`PRJ-22`)** — `image.repository` and `imagePullSecrets[0].name`
  tokenized to `@@REGISTRY@@` / `@@PULL_SECRET@@`; the `deploy/Dockerfile` header comment
  named the same registry and now names the token; `docs/contracts.md` (this repo's) extends
  the scaffold-token list, which is a contract surface.

**Why.** The first two are the same failure in two forms: the pairing of the `/metrics`
handler with the chart's `ServiceMonitor` is already stated in `docs/contracts.md` to be *the*
contract of the `service` scaffold, and neither the scaffold's own registry nor its unit tests
reflected it. A scrape against a path that stopped being served fails silently — no red test,
no alert, an empty panel weeks later — so the tiers that could catch it are the only thing
between that and a release. The third is the host-agnosticism rule (`PRJ-14`, `PRJ-19`) applied
to the one file that had escaped it.

**The decision inside `PRJ-22`, recorded because it looks like a coin flip and is not.** Two
mechanisms could carry a registry token: a `repo.env` key taught to `compose.sh`, or a
scaffold-instantiation token. The standard already answers it. `compose.sh` substitutes into
`CLAUDE.md` and nothing else, so it would never resolve a token in `values.yaml`; a key added
to `standard/repo.env.example` would therefore be read by nobody while implying the opposite,
and `docs/contracts.md` separately records that a new required `repo.env` key breaks every
existing one simultaneously, one committed file per repository. The scaffold-token mechanism —
`@@CI_TEMPLATES_PROJECT@@`, `@@CI_TEMPLATES_REF@@`, `@@RUNNER_TAG@@` — exists for exactly this
and already has its own enforcement in each scaffold's adoption step. No new machinery.

**Verified by.** `./standard/compose.sh --check` → `OK: CLAUDE.md matches standard/
(profile=service)`, exit 0. `pytest` → 14 passed, total coverage 92.19 % against the 80 % floor.
The `service` scaffold instantiated into a throwaway copy twice (GHCR and GitLab flavours):
`grep -rnE '@{2}' .` empty, `pytest` 12 passed, `ruff` clean, `mypy` clean under
`disallow_untyped_defs`, `helm lint` 0 charts failed, and `helm template` rendering
`ghcr.io/acme/services/demo-service:0.0.0` + `ghcr-pull` and
`registry.gitlab.com/…` + `gitlab-registry` respectively. Raw, unsubstituted `values.yaml`
still parses as YAML — the reason both tokens are quoted. The generator's hard fail was
re-proved on a throwaway copy of `standard/`: an injected `@@REGISTRY@@` in a profile source
exits 1 naming the token, and neither token appears under `standard/` in the real repo.
`helm lint` on the *unsubstituted* scaffold fails, as it always has — `@` cannot open a plain
scalar — which is why the lint was run against instantiated copies.

**Reverse.** Revert `c74a09e`, `175b865`, `b72491c`. Nothing outside `templates/service/`,
`docs/contracts.md` and this file was touched, and no generated file changed.

**Open.** Still no CI run: unchanged from the entry below, there is no runner. Everything here
is local. The GitLab mirror `korkin25/ai-project-template` **does now exist** and accepted all
three pushes, which retires half of `PRJ-17`; the parity pipeline it asks for has still never
executed. `templates/{platform,infra}/` were not audited for the same hardcoded registry — the
`platform` scaffold still carries `gitlab-registry` in `requirements.yaml`, `bundle.yaml` and
`values/common.yaml`, and `infra/docs/contracts.md` documents that name as a contract. That is
a separate change and it needs the infra/platform pair moved together.

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
