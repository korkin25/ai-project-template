# Contracts — ai-project-template

A **contract** is anything outside this repo depends on: a message topic and its schema, a
database table this repo writes, an HTTP or MCP endpoint, a symbol exported from a published
library. This file is the local half of the registry — the platform repo holds the
system-wide view — and it is the half that must never go stale, because a consumer reads it
*instead of* reading this repo's source. Everything it does not describe is something they
were never promised.

**This repo publishes no topic, no table and no endpoint.** What it publishes is **the
standard itself**: the rule sources, the generator that turns them into a `CLAUDE.md`, the
placeholder vocabulary that generator understands, the scaffold layouts, and the skills.
Every repository created from here **vendors a copy** of those, which makes them as much a
contract as a Kafka topic and considerably harder to migrate — there is no version pin, no
import graph and no compiler. A rename here does not fail anybody's build. It silently
desynchronises a dozen repositories, and the symptom surfaces weeks later as a drift-gate
failure in a repo whose author changed nothing.

The rule that follows: **a change to anything below is breaking until you have shown it is
not**, and *propagation is part of the change*, not a follow-up.

---

## Owned by this repo

### The rule sources — `standard/base.md`, `standard/profiles/<profile>.md`

The text every repo's `CLAUDE.md` is composed from. `base.md` binds every profile;
`profiles/{service,library,platform,infra}.md` bind one kind of repo each.

| What consumers rely on | Breaking it looks like |
|---|---|
| The **four profile names**, each with a file at `standard/profiles/<name>.md` | Renaming or removing a profile makes `compose.sh` refuse to run in every repo pinned to it — `repo.env` names a profile that no longer has a file |
| The **section headings** — *Cross-repo contracts*, *Per-task lifecycle*, *Documentation sync*, *Keeping deployed versions current*, *Safe autonomy* | Docs, skills and hooks in consuming repos cite these by name; a renamed section turns every citation into a dangling reference no tool checks |
| The **paths the rules mandate** — `docs/{architecture,configuration,tests,contracts}.md`, `TODO.md`, `CHANGELOG.md`, `AUTOPILOT-LOG.md`, `auto-tests/group-{a,b,c}/`, `.versions/*.env` | Moving a mandated path orphans the file that already exists in a dozen repos, and the doc-sync guard keeps matching the old one |

Adding a rule is additive and safe. Removing one, renaming a section, or changing what a
mandated path means is not — and there is no consumer that finds out by failing to compile.

### The generator CLI — `standard/compose.sh`

```
./standard/compose.sh            # read standard/repo.env, write CLAUDE.md at the repo root
./standard/compose.sh --check    # regenerate in memory and diff against the committed file
./standard/compose.sh --stdout   # print, write nothing
```

| Surface | Guarantee |
|---|---|
| Exit codes | `0` ok · `1` usage or config error · `2` drift (`--check` only) |
| Input path | `standard/repo.env`, resolved relative to the script, never to the caller's cwd |
| Output path | `CLAUDE.md` at the repo root — nowhere else, and never a second file |
| `repo.env` handling | **parsed, never sourced** |

The three exit codes are the load-bearing part. The `standard-drift` gate is
`compose.sh --check`, and a CI job that only distinguishes zero from non-zero cannot tell
"the committed file drifted" from "`repo.env` is missing a key" — two findings with opposite
remedies. Collapsing them silently degrades the gate into a red X with no diagnosis.

`repo.env` is parsed rather than sourced deliberately: it is committed configuration, and a
config file that can execute arbitrary shell is a supply-chain hole in the standard's own
tooling. Any consumer writing their own reader must keep that property.

### `standard/repo.env` — the input format

Strict `KEY=value`, one per line. `#` comments and blank lines allowed; the value is the
rest of the line verbatim minus optional surrounding quotes, so it may contain spaces and
needs no escaping; last assignment wins.

| Key | Required | Validated as |
|---|---|---|
| `PROFILE` | yes | lowercase letters and hyphens; must name an existing `standard/profiles/<PROFILE>.md` |
| `PROJECT` | yes | non-empty — the hyphenated repo/image/chart name |
| `PKG` | yes | non-empty — the underscored Python package name |
| `TICKET_PREFIX` | yes | uppercase `A-Z0-9`; unique across the whole group |
| `GROUP` | yes | non-empty |
| `DESCRIPTION` | yes | non-empty |
| `DIST_NAME` | no | defaults to `PROJECT` — the published distribution name |

**Adding a required key breaks every existing `repo.env` simultaneously.** Each one is a
committed file in a different repository, so the fix is a branch and an MR per repo, none of
which the author of the new key will open. New keys are optional with a default, or they are
a migration with a ticket in every consuming repo.

### The `@@…@@` placeholder vocabulary

`compose.sh` substitutes exactly seven tokens:

```
@@PROFILE@@  @@PROJECT@@  @@PKG@@  @@PREFIX@@  @@GROUP@@  @@DESCRIPTION@@  @@DIST@@
```

and then **hard-fails if any `@@` survives**, printing every leftover token. That check is
what makes a missed placeholder a build error instead of a repo whose rulebook tells agents
to open `@@PROJECT@@`.

The invariant it imposes is easy to break by accident and worth stating outright:

> Tokens `compose.sh` does not know — today `@@CI_TEMPLATES_PROJECT@@`, `@@CI_TEMPLATES_REF@@`
> and `@@RUNNER_TAG@@` — may appear **only under `templates/`**, never under `standard/`.

They are scaffold-instantiation tokens, substituted by whoever creates the new repo, not by
the generator. Writing one into `standard/**` does not fail here — this repo regenerates
against its own `repo.env` just fine only if the token happens to be known — it fails in
every consuming repo at once, on their next regeneration, as an error about a token they
never wrote. Teaching `compose.sh` a new token is therefore a prerequisite of using it in
the rule sources, in the same change.

### The generated `CLAUDE.md` format

The composed file opens with a six-line HTML comment naming its sources, its profile, a
`Sources-SHA256`, and the regeneration command. The checksum covers the **sources**
(`base.md` + the profile + `repo.env`, concatenated), not the rendered output, so
reformatting the generated file is caught as drift too.

Around that file sits the multi-agent pickup set — six symlinks and one pointer, all
resolving to the same rulebook:

| Consumer | File |
|---|---|
| Codex / generic | `AGENTS.md` → `CLAUDE.md` |
| Gemini | `GEMINI.md` → `CLAUDE.md` |
| Cursor | `.cursorrules` → `CLAUDE.md`, plus `.cursor/rules/project.mdc` (a thin MDC pointer, not a symlink) |
| Cline | `.clinerules` → `CLAUDE.md` |
| Windsurf | `.windsurfrules` → `CLAUDE.md` |
| Copilot | `.github/copilot-instructions.md` → `../CLAUDE.md` |

Renaming `CLAUDE.md`, or moving it off the repo root, breaks all seven at once across six
runtimes — and it breaks them *silently*: a dangling rules file is not an error in any of
them, it is an agent that loads no rules and behaves like it never had any.

### The scaffold layouts — `templates/<profile>/`

The directory trees a new repo is created from. **The paths are the contract**, because
shared CI templates and the doc-sync guard match on them:

```
service   deploy/Dockerfile · helm/ · src/@@PKG@@/ · .versions/ · auto-tests/group-{a,b,c}/
library   src/@@PKG@@/ · tests/test_public_api.py · docs/contracts.md (enforced registry)
platform  clusters/<cluster>/environments/<env>/bundle.yaml · requirements.yaml · scripts/
infra     manifests/ · scripts/check-versions.py · docs/runbook.md
```

Every profile additionally carries `standard/repo.env`, `docs/{architecture,configuration,
tests}.md`, `TODO.md`, `CHANGELOG.md`, `AUTOPILOT-LOG.md`, `.gitlab-ci.yml`.

**In the `service` scaffold, `GET /metrics` and the chart's `ServiceMonitor` are one unit.**
`src/@@PKG@@/main.py` serves the endpoint on the same port as `/health`,
`helm/templates/servicemonitor.yaml` scrapes it, and `helm/values.yaml` gates it behind
`serviceMonitor.enabled: false` because the CRD is a cluster prerequisite. The *pairing* is
the contract, not either file: ship the ServiceMonitor without the handler and every repo
built from the scaffold gets a target that 404s — discovered, scraped, storing nothing, with
no alert to fire because the alert needs the series that never arrived. Ship the handler
without the ServiceMonitor and the endpoint is never read at all. `standard/profiles/service.md`
requires both of *every* service, so the scaffold is where that promise is either kept or
quietly broken for the whole fleet at once.

Moving a path in a scaffold does not migrate the repos already built from it — it forks
them. From that day the scaffold and the fleet disagree, and the next person to compare them
cannot tell which side is the mistake.

### The service ↔ platform version interface

Specified in `standard/base.md`; produced by each service repo's CI; read by the platform
repo. This repo owns the **specification**, which is why a key rename here breaks a reader in
a repo nobody touched.

| File | Keys |
|---|---|
| `.versions/docker-image.env` | `CI_REGISTRY_IMAGE`, `CI_REGISTRY_IMAGE_TAG`, `IMAGE_REF`, `IMAGE_DIGEST` |
| `.versions/helm-chart.env` | `CHART_NAME`, `CHART_VERSION`, `APP_VERSION`, `HELM_OCI_URL` |

Invariant: **chart version == image tag == `GitVersion_SemVer`** — one commit, one version,
everywhere. Generated by CI, never hand-edited.

### The skills

Portable [Agent Skills](https://agentskills.io) `SKILL.md` files, frontmatter deliberately
restricted to the two core fields (`name`, `description`) so any compatible runtime reads
them unchanged.

| Skill | Consumed as |
|---|---|
| `cluster-version-audit` | monthly substrate audit — CNI, cert-manager, secrets operator, GitOps controller, CRDs |
| `data-plane-version-audit` | monthly stateful audit — database, message bus, vector store, cache, CDC |
| `example-skill` | the authoring template |

**The directory name is the install name**, cited from `standard/base.md` and from consuming
repos' docs; renaming one breaks every installed copy and every citation. The `description`
is subtler and matters more: it is the routing key an agent matches a request against.
Weakening it does not produce an error anywhere — the skill simply stops being selected, and
the work it was meant to gate gets done ad-hoc by an agent that never read it.

Distribution manifests, whose names consumers type verbatim:

```
/plugin marketplace add <owner>/<repo>     # .claude-plugin/marketplace.json — "app-marketplace"
/plugin install app@app-marketplace        # .claude-plugin/plugin.json      — "app"
```

Renaming either identifier breaks every existing install.

**Neither manifest declares a `version`, deliberately.** The field is optional in both, and
resolution falls back to the source's git commit SHA — so every commit is a new version and
installs track the repository. The previous hardcoded `0.1.0` was not only a breach of the
never-hardcode-a-version rule; it was actively broken, because a pinned version means users
receive an update *only* when the string is bumped, and every install was therefore frozen at
`0.1.0` forever. Re-adding a version is the natural instinct and it is the bug.

The end state is CI injecting `GitVersion_SemVer` at package time, which would put the plugin
under the same one-commit-one-version invariant as the image and the chart. The SHA fallback
gives per-commit granularity instead of per-release — good enough that this is a follow-up,
not a blocker.

### Known consumers

An unlisted consumer is one that gets broken. Keep this current — it is the blast radius a
proposed change is measured against, and the list of tickets to open.

| Repo | Vendors | Profile | In sync? |
|---|---|---|---|
| `job-agent/infra/dev-stack` | its own copy of `standard/` + generated `CLAUDE.md` | `infra` | unverified — no gate spans repos (`PRJ-2`) |

Because the standard is **vendored, not referenced**, there is no pin for a consumer to bump
and nothing tells them a new version exists. They keep running the old rules until someone
regenerates. Until every listed repo has been regenerated, the group is running two
standards and neither is authoritative.

---

## Consumed from other repos

Pin the version you tested against, and rely only on what the owning repo documents.
Behaviour observed but never promised is not a contract; needing it is a request to that
repo, not an assumption here.

| Contract | Owner | Pinned at | Used for |
|---|---|---|---|
| Reusable workflows `python·sast·docker·helm·functional`, actions `detect-project`, `gitversion` | `korkin25/open-ci-actions` | `@v1` — **moving major tag** | the whole of `.github/workflows/ci.yml` |
| Shared templates `/globals·/auto-semversioning·/lint·/sast·/docker-build·/helm-package·/functional` | `open_ci_cd/templates` (GitLab) | `ref: main` — **moving branch** | the whole of `.gitlab-ci.yml` |
| GitVersion 6.x config schema + the `GitVersion_SemVer` output variable | GitTools | `gittools/actions/*@v3`, image `gittools/gitversion:6.3.0` | every version in the repo |
| `SKILL.md` frontmatter spec (`name`, `description`) | agentskills.io | core fields only, by choice | `skills/*/SKILL.md` portability |
| Plugin + marketplace manifest schema | Claude Code | — | `.claude-plugin/*.json` |
| gitleaks | `zricethezav/gitleaks` | `v8.30.1`, exact | the only local pre-commit hook, run via Docker |
| Python base image | Docker Official | `python:3.12-slim` via `ARG PYTHON_VERSION` | both Dockerfile stages |
| GHCR | GitHub | — | image + OCI chart registry |
| `hatchling`; dev extras `pytest>=8`, `pytest-cov>=5`, `ruff>=0.5`, `mypy>=1.10`, `bandit>=1.7`, `pip-audit>=2.7`, `build` | PyPI | floor pins, moved weekly by Dependabot, majors excluded | build + quality gates |

Two of those track a moving ref. **That is a recorded decision, not an oversight**: shared CI
is executed code from another repository running with this repo's credentials, and a moving
ref means an upgrade lands here without an MR. The blast radius is the whole pipeline; the
mitigation is that the consumed surface is the *job names and their inputs*, never internals,
so a template refactor cannot reach us. `.gitlab-ci.yml` says to pin `ref` to a tag on
adoption, and the reason it does not today is that the templates repo has no tag carrying
every included file — check that before changing it.

**Never edit a shared template from here.** A change needed there is a ticket in that repo.

---

## Changing a contract you own

1. **Design it as a platform decision.** Open a decision ticket: what changes, who consumes
   it today, whether the change is compatible, and the migration path. A breaking contract
   change is architectural and **requires the user's approval**.
2. **Prefer additive.** Add a rule, a key, a token, a profile — do not repurpose one. A new
   `repo.env` key gets a default; a new placeholder is taught to `compose.sh` in the same
   change. A consumer you forgot about must keep working.
3. **Producer first, then consumers, then remove.** Ship the generator understanding both
   the old and the new shape, move every repo, only then delete the old shape. Never invert
   that order — here the consumers are on their own schedule and cannot be moved atomically.
4. **Open the consumer tickets yourself**, one per affected repo, each citing the platform
   id. An unannounced contract change is the most expensive mistake available here, and for
   a vendored standard it is also the quietest: nothing breaks until someone regenerates.
5. **Update this file on both sides**, in the same change as the code — and regenerate
   `CLAUDE.md` everywhere the sources moved. Propagation is part of the change.

---

## What is deliberately *not* a contract

Stated explicitly because these look exactly like the endpoints, images and charts that
**are** contracts in a real service repo — and mistaking scaffolding for a promise is how a
placeholder ends up pinned in production:

| Not a contract | Why it exists |
|---|---|
| `src/app/` — the `GET /health` and `GET /metrics` endpoints, the `APP_VERSION` variable, the `app` / `app-serve` commands | a sample service that keeps this repo's own CI green and demonstrates the shape; replaced on adoption. What *is* binding is the profile rule they demonstrate (below), not this implementation of it |
| `helm/` values — `ghcr.io/OWNER/REPO`, `tag: ""` | template placeholders; `OWNER/REPO` is not a registry path |
| `docker-compose.yml` — `image: ghcr.io/OWNER/REPO:latest` | local-run convenience. A version auditor reading this repo flags it as `UNPINNED`; that finding is about a placeholder, not about a deployed image |
| `.claude-plugin` plugin version | absent on purpose; resolution falls back to the commit SHA. Not an interface, and re-adding it would freeze every install |

Nothing outside this repo may depend on any of them.
