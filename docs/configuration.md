# Configuration — environment variables

Everything the service needs at runtime is configured through environment variables, never a
file baked into the image — an image that carries its own config is an image that has to be
rebuilt to move between environments. Nothing sensitive is committed; secrets arrive from the
environment: locally from Docker/compose, in the cluster by reference to an existing Secret
via the chart's `envFrom.secret`, and in CI from the host's own variable store (see
*CI functional tests* below).

Update this file **in the same change** whenever you add or rename a runtime env var
(Documentation-sync rule).

**Do not expect the doc-sync gate to catch you.** It asks one question — did *any* file under
`docs/`, `README`, `CHANGELOG`, `TODO`, `CLAUDE.md` or `AUTOPILOT-LOG.md` change alongside the
code? — and it cannot ask whether the *right* doc changed. `APP_VERSION` and `GET /metrics`
below both shipped with the gate green, because the same commit edited `CLAUDE.md`; they were
undocumented for a release anyway. The gate stops a change that documents *nothing*. Only a
reviewer stops one that documents the wrong thing, so read the table, not the check mark.

## Sample app (`app-serve`)

| Variable | Default | Secret | Purpose |
|----------|---------|:------:|---------|
| `APP_HOST` | `0.0.0.0` | | Bind host for the HTTP service. |
| `APP_PORT` | `8080` | | Bind port for the HTTP service. |
| `APP_VERSION` | packaged `__version__` (`0.0.0`) | | The version reported by `GET /health` and by the `app_build_info` series on `GET /metrics`. **Set by the chart from `.Chart.AppVersion`**, i.e. the released SemVer — the image cannot know its own tag, so the packaged constant is only the fallback for a local run. An empty value is treated as unset: `APP_VERSION=""` from a ConfigMap key with no value would otherwise report a blank version that still looks like a valid response. |

The chart sets it as a container `env` entry, never through `envFrom`, so nothing in a shared
ConfigMap can shadow it — see `helm/templates/deployment.yaml`.

## Tests

| Variable | Default | Purpose |
|----------|---------|---------|
| `APP_LIVE` | unset | Set to `1` to enable any gated live tests you add. |

## CI functional tests

**The concept, which is the same on every host:** the `functional` job boots the image CI just
built and drives it from outside, so it needs the same variables the container needs at
runtime. Those live in the CI host's variable store, scoped as narrowly as the host allows —
never in the repository, and never inlined into the pipeline file, where a value becomes both
unreviewable and permanent.

What this repo's job needs:

- **Variable** `APP_PORT` — the port the functional job probes (default `8080`).
- **Secrets** — none for the sample. Add yours here as your service grows, and keep the job
  guarded so it **skips cleanly** when a secret is absent. Forks and freshly-cloned repos have
  no secrets by definition; a job that hard-fails there is a permanently red check that
  everyone learns to scroll past, which costs more than the test was worth.

**The mechanics, which differ.** The standard takes no side; a project picks one host and
records it in [architecture.md](architecture.md).

| | GitLab | GitHub |
|---|---|---|
| Where values live | project (or group) CI/CD variables | repository or organization variables |
| Scoping | an **environment scope** on the variable (`ci-functional`) | an **environment** named `ci-functional`, holding its own variables |
| Secret vs plain | one store; a secret is a variable marked **masked** (and usually **protected**) | two stores — variables and secrets — with secrets write-only after creation |
| Set a variable | `glab variable set APP_PORT 8080 --scope ci-functional` | `gh variable set APP_PORT --env ci-functional --body "8080"` |
| Set a secret | `glab variable set MY_TOKEN --masked --protected --scope ci-functional` | `gh secret set MY_TOKEN --env ci-functional` |

Both secret commands read the value from **stdin** when none is given on the command line, so
the token never lands in your shell history.
| Read it in a job | `$APP_PORT` | `${{ vars.APP_PORT }}` / `${{ secrets.MY_TOKEN }}` |

The difference worth knowing is the last one in the "secret vs plain" row. GitHub keeps
secrets in a separate, write-only store, so a wrong value is replaced rather than inspected.
GitLab keeps everything in one place and *masking is opt-in* — an unmasked secret is a normal
variable that will be echoed into a job log the first time something prints the environment.
Set `masked` when you create it, not after: the log that already leaked it is not retroactively
redacted.

## Branch protection (GitLab) — the branch model, made real

`CLAUDE.md` states the branch model as a fact: `feature/*` → `dev` → `rc` → `release`, **no
`main`**, **no tags**, every promotion approval-gated. None of that is true until someone
configures the project. Until then it is a convention, and a convention is exactly as strong
as the least careful push.

The commands below turn it into project state. They are **written down rather than automated**
on purpose:

- Protection is **per-project setup state**, applied once when the project is created — not a
  thing that drifts on every commit and needs reconciling. The cost of doing it by hand is one
  paste; the cost of automating it is a job holding an **Owner-scoped token**, because none of
  these endpoints accept `CI_JOB_TOKEN`. A credential that can rewrite branch protection,
  living permanently in CI so that nobody ever has to paste four commands, is a worse trade
  than the four commands.
- `POST /protected_branches` is **not idempotent** — re-running it on an already-protected
  branch returns `409 Conflict`. Any "just re-apply it" automation therefore needs
  delete-then-recreate logic, and a script that unprotects a branch before reprotecting it has
  a window in which `release` is writable by anyone. That window is worth more than the
  convenience.

What this section is **not**: the GitHub half. The host table promises `CODEOWNERS` plus
required reviewers on both hosts, and GitLab was the side with nothing written down at all.
The GitHub branch-protection recipe is a separate gap — do not read this section's existence
as evidence that it is covered.

### Before you start

```bash
glab auth status                     # must show a token for the right host
PROJECT='group%2Fsubgroup%2Fproject' # URL-encoded full path, or the numeric project id
```

The `%2F` is not optional: the project path goes into a URL path segment, and an un-encoded
slash makes GitLab route the request somewhere else entirely and answer `404` — which reads
exactly like "you have no access", and sends you to look at the wrong problem.

Every command below is `glab api`. `glab` 1.36 has **no** `protected-branch` command (see
`glab --help`), so the REST API is the interface, not a fallback. `--field` infers the JSON
type — bare integers and `true`/`false` are sent as numbers and booleans, which these
endpoints require; a quoted `"0"` is rejected.

### 1. Project-level merge rules, and `dev` as the default branch

```bash
glab api --method PUT "projects/$PROJECT" \
  --field default_branch=dev \
  --field only_allow_merge_if_pipeline_succeeds=true \
  --field only_allow_merge_if_all_discussions_are_resolved=true \
  --field merge_method=merge \
  --field squash_option=never \
  --field remove_source_branch_after_merge=true
```

- `default_branch=dev` **goes first**, before step 4: GitLab refuses to delete the default
  branch, so `main` cannot be removed while it still holds that role.
- `only_allow_merge_if_pipeline_succeeds` is what makes "merge only when CI is green"
  mechanical instead of aspirational — and it is the switch that gives `doc-sync` and
  `standard-drift` their teeth. A gate that can be merged past is a gate that will be.
- `merge_method=merge` is the `--no-ff` the workflow asks for: it preserves the merge commit.
- `squash_option=never` is **load-bearing, not taste**. GitVersion derives every version in
  this repo from the branch graph. Squashing a feature branch into `dev` destroys the
  topology it reads, and the symptom is not an error — it is a version number that is quietly
  wrong on an artifact that is already published.

### 2. Protect `dev`, `rc` and `release`

```bash
for br in dev rc release; do
  glab api --method POST "projects/$PROJECT/protected_branches" \
    --field "name=$br" \
    --field push_access_level=0 \
    --field merge_access_level=40 \
    --field allow_force_push=false \
    --field code_owner_approval_required=true
done
```

Access levels are integers: **`0` = no one · `30` = Developer · `40` = Maintainer**.

- `push_access_level=0` — **nobody pushes directly**, not even a Maintainer, not even you at
  23:50. Changes arrive only through a merge request, which is the only place review, the
  approval rules and the two gates exist at all.
- `merge_access_level=40` — Maintainers merge; Developers open MRs.
- `allow_force_push=false` — a force push to `dev` rewrites the history GitVersion computes
  from, and rewrites it for everyone who already pulled it. The default is already `false`;
  it is stated because a default nobody wrote down is a default somebody will flip.
- `code_owner_approval_required=true` — **this is the switch that makes `.gitlab/CODEOWNERS`
  binding.** Without it the file is parsed, displayed, and enforces nothing: the rules look
  live and the merge button stays green. Requires Premium/Ultimate, as does Code Owners
  itself; on Free, omit this field and know that ownership is documentation.

### 3. Forbid tags outright

```bash
glab api --method POST "projects/$PROJECT/protected_tags" \
  --field 'name=*' \
  --field create_access_level=0
```

Quote the `*` or the shell expands it against your working directory and you protect a tag
named after whatever file sorts first.

Releasing here is a **merge, not a tag**: merging to `rc` publishes a pre-release, merging to
`release` publishes the stable version, and GitVersion computes both from the branch graph
plus `next-version` *precisely because there are no tags to read*. One stray tag silently
changes every version computed after it — on artifacts that are already published and cannot
be replaced. `create_access_level=0` removes the possibility rather than the habit.

### 4. Remove `main`, and stop it coming back

```bash
glab api --method DELETE "projects/$PROJECT/repository/branches/main"

glab api --method POST "projects/$PROJECT/protected_branches" \
  --field name=main \
  --field push_access_level=0 \
  --field merge_access_level=0
```

The second command is the part people skip. Deleting `main` removes today's branch; it does
nothing about the next clone that pushes one, or the tool that helpfully creates it. GitLab
treats *creating* a branch that matches a protected pattern as a push to it, so protecting the
name with "no one" allowed to push means the name cannot be recreated. A repo where `main`
reappears is a repo where half the tooling starts targeting a branch nothing builds.

### 5. Verify — the step that is actually the point

```bash
glab api --paginate "projects/$PROJECT/protected_branches" \
  | jq -r '.[] | "\(.name)  push=\(.push_access_levels[0].access_level)  merge=\(.merge_access_levels[0].access_level)  force_push=\(.allow_force_push)  codeowners=\(.code_owner_approval_required)"'

glab api --paginate "projects/$PROJECT/protected_tags" \
  | jq -r '.[] | "\(.name)  create=\(.create_access_levels[0].access_level)"'

glab api "projects/$PROJECT" \
  | jq -r '{default_branch, merge_method, squash_option, only_allow_merge_if_pipeline_succeeds}'
```

Expect three protected branches with `push=0`, `main` present with `push=0` and `merge=0`, one
protected tag pattern `*` with `create=0`, and `default_branch: "dev"`. Read the output rather
than the exit codes: `glab api` prints GitLab's error body and still exits `0` on some
responses, so "the command ran" is not the same as "the setting took".

### Premium-only extras

These need Premium/Ultimate and fail cleanly on Free — apply them if you have it, and if you
do not, know which of the standard's guarantees you are running on trust:

```bash
glab api --method POST "projects/$PROJECT/approvals" \
  --field merge_requests_author_approval=false \
  --field reset_approvals_on_push=true
```

`merge_requests_author_approval=false` stops an author approving their own MR, which is the
whole content of "approval-gated" for a repo with one active person.
`reset_approvals_on_push=true` drops approvals when new commits land — without it, an MR
approved at diff A can be merged as diff B, and the approval that was given is not the change
that shipped.
