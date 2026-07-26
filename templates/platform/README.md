# @@PROJECT@@

@@DESCRIPTION@@

The **integration truth** for the system: the one repository that can answer *what is
actually running, where, at which version*. It follows the **platform** profile of the shared
standard (`standard/profiles/platform.md`). It holds no application code, builds no image and
publishes no package — its released artifact is **the state of an environment**, and a
release is a merge.

| | |
|---|---|
| The descriptor | `clusters/<cluster>/environments/<env>/bundle.yaml` — what runs here, at which version |
| What it needs from the cluster | [`requirements.yaml`](requirements.yaml) — capabilities an `infra` repo must satisfy |
| The registry | [`docs/contracts.md`](docs/contracts.md) — every contract, its owner, its consumers |
| Cross-service tests | [`e2e/`](e2e/) — tier (d), the only place they can live |
| Rules | [`CLAUDE.md`](CLAUDE.md) — generated from `standard/` |

> **CI validates. It never deploys.** Flux reconciles from git, so a pipeline holding cluster
> credentials would create a second writer and defeat the pull model. **The merge is the
> deployment**, and `git revert` is the rollback.

## Scope — the two boundaries that keep this repo honest

**Downwards, to the `infra` repo.** This repo assumes a working cluster and consumes it. The
CNI, the ingress/gateway, cert-manager, the secrets operator and the GitOps controller itself
belong to the infra repo; a missing platform component is a ticket *there*, never a manifest
here. `requirements.yaml` is the machine-readable form of that boundary, and
`scripts/check-requirements.py` is how you find out it is unmet **before** deploying rather
than as a `CrashLoopBackOff` an hour later.

**Sideways, to each service repo.** A chart ships from the service it deploys; this repo only
**pins** a version of it. A platform repo that carries a service's chart has taken ownership of
something it cannot keep in step with that service's code.

Both directions are stated again in [`docs/architecture.md`](docs/architecture.md), naming the
actual repos — the overlap between "install the operator" and "deploy the thing that needs the
operator" is the single most common source of duplicated, conflicting manifests.

## Features

> What this repo provides to everyone else. Engineering history belongs in
> [`CHANGELOG.md`](CHANGELOG.md), open work in [`TODO.md`](TODO.md).

- **A diffable statement of every environment.** One tree, one commit, one answer to "what is
  in dev". Environments are directories, not branches.
- **A declared infrastructure contract** (`requirements.yaml`) that a live cluster can be
  checked against, so an unmet prerequisite has a name and an owner.
- **Cross-service end-to-end tests** that no single service repo can run.

## Adopting this scaffold

1. **Replace every placeholder token:**

   | Token | What it becomes |
   |---|---|
   | `@@PROJECT@@` | hyphenated repo name — also how the platform is named in bundles and namespaces |
   | `@@PKG@@` | underscored form of `@@PROJECT@@`. Nothing imports it (see `standard/repo.env`), but `compose.sh` requires it |
   | `@@PREFIX@@` | ticket prefix, uppercase — **this is the platform id every other repo cites** |
   | `@@GROUP@@` | GitLab namespace that owns the repo |
   | `@@DESCRIPTION@@` | the one-line description, used in the generated `CLAUDE.md` |
   | `@@CI_TEMPLATES_PROJECT@@` | the shared CI-templates repo, as a GitLab project path |
   | `@@CI_TEMPLATES_REF@@` | the ref of it to track — prefer a tag; see the note in `.gitlab-ci.yml` |
   | `@@RUNNER_TAG@@` | the tag of your runner fleet — it appears in **two blocks** of `.gitlab-ci.yml` that must stay in sync |

   `grep -rnE '@{2}' . --exclude-dir=standard` must come back empty when you are done. The
   exclusion is not a loophole: the vendored `standard/` sources legitimately carry
   `@@PROFILE@@`, which `compose.sh` substitutes while generating `CLAUDE.md` — and it
   hard-fails if any token it does not know survives, so a missed placeholder there is a
   build error rather than a rulebook telling agents to open `@@PROJECT@@`.

2. Run `./standard/compose.sh` to generate `CLAUDE.md`, and commit it.

3. **Rename `clusters/example-cluster/`** to the real cluster — use the kubecontext name, so
   the directory and the thing a human types are the same string — and rename the scaffold
   values inside it: `example-platform` (the bundle `name` prefix and the `namespace`),
   `example-service`, and the `<registry>/<group>` placeholders in `imageRegistry` and
   `repoURL`. Rename `values/example-service.yaml` in the same change:
   `validate-bundles.py` reports an unreferenced values file as a dead file, and a bundle
   entry with no values file as a probable typo.

   Those three are literal strings rather than substituted tokens on purpose:
   `bundle.schema.json` constrains `name` and `namespace` to DNS labels and
   `validate-bundles.py` requires the bundle name to contain its environment directory name,
   so a token carrying `@` would fail this repo's own gate on the very first pipeline —
   before anyone had a chance to read why.

4. Rename the API group and `metadata.name` in [`requirements.yaml`](requirements.yaml), and
   cut it down to what this platform genuinely needs. **Every entry left in it is a demand on
   another team**, so an inherited requirement nobody uses is an infra ticket nobody should
   have opened.

5. Run `python3 scripts/check-requirements.py --context <cluster>` against the target cluster
   and open the gaps as tickets in the infra repo, citing `@@PREFIX@@` ids. Do this *before*
   the first bundle bump; the alternative is discovering the missing `ClusterSecretStore` from
   a pod event.

## Layout

```
clusters/<cluster>/environments/<env>/
  bundle.yaml            THE descriptor — what runs here, at which version
  values/common.yaml     defaults applied to every chart in this environment
  values/<name>.yaml     per-component overrides; the filename IS the bundle entry name
  manifests/             raw resources that are not a service chart (DB clusters, topics,
                         ExternalSecrets), one directory per component
bundle.schema.json       JSON Schema, additionalProperties: false throughout
requirements.yaml        what this platform needs from whatever cluster it runs on
scripts/validate-bundles.py    schema gate + the checks a schema cannot express
scripts/render.py              bundle.yaml -> Flux OCIRepository + HelmRelease
scripts/check-requirements.py  the same contract, checked against a live cluster
e2e/                     tier-(d) cross-service tests — see its README
auto-tests/group-b/      plan/verify scenarios run against a real environment
auto-tests/group-c/      human-in-the-loop methodologies
docs/                    architecture, configuration, contracts, environments, tests
standard/                the shared rulebook's sources + this repo's identity
```

## Working here

```bash
pip install pyyaml jsonschema      # everything scripts/ needs

# Exactly what CI runs, in the order CI runs it.
yamllint .
python3 scripts/validate-bundles.py
python3 scripts/render.py --all | head -50

# What the cluster is missing, before deploying anything into it.
python3 scripts/check-requirements.py --context <cluster>

# There is no apply step, locally or in CI. Merging is the deployment.
```

The rendered output is **never committed**. It is derived from the bundle, and a committed
render is a second source of truth that is wrong the moment someone edits one of the two.

## Deploying, promoting, rolling back

- **Deploy** = read the service's committed `.versions/helm-chart.env`, set that exact
  `chartVersion` in the target environment's `bundle.yaml`, open an MR. That MR is the
  deployment. Never a version typed from memory, never a range.
- **Promote** = copy a version from one environment directory to the next, after tier-(d) is
  green in the source environment. Never a rebuild, never a retag — the artifact that was
  tested is the artifact that moves.
- **Roll back** = `git revert` the MR. If a rollback ever needs anything else, the model has
  been broken somewhere; fix that rather than working around it.
- **Every version bump needs human approval.** It is a deployment, not an edit — this is the
  one repo where a one-character diff changes what is running in a shared environment.

## Secrets

No secret value is ever committed. Secrets are declared by *reference* and resolved
in-cluster by the External Secrets Operator against a `ClusterSecretStore`; keys resolve
under `{vaultPathPrefix}/…` from the bundle, so a dev environment structurally cannot read
production keys. The full procedure is in [`docs/configuration.md`](docs/configuration.md).
