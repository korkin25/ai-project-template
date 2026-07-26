# Architecture — @@PROJECT@@

> **Design-before-code lives here.** No change is made until the design is written down: what
> it changes, what depends on it, how it is verified, and how it is undone. In this repo the
> last one is usually short — a `git revert` — and it stays short only because every other
> rule below is kept.

## What this repo owns

The **integration truth**: the answer to *what is running, where, at which version*. No
application code, no image, no published package. Its released artifact is the state of an
environment, and a release is a merge.

- The **bundle** for each environment — the declarative list of what is deployed and at which
  version.
- **Per-environment values** for every chart.
- The **system-wide view**: how the services fit together, the contract registry
  ([contracts.md](contracts.md)), and the cross-repo decision log below.
- **Tier-(d) cross-service end-to-end tests** ([`../e2e/`](../e2e/)).
- The **infrastructure contract** ([`../requirements.yaml`](../requirements.yaml)) — what this
  platform demands of whatever cluster it lands on.

## What this repo does NOT own

Two boundaries, and both are worth stating in full because the failure mode is the same on
each side: something gets deployed twice, from two repos, at two versions, and the cluster
resolves the conflict by whichever reconciler ran last.

**Below — the cluster itself, owned by the infra repo.** Cluster bootstrap, the CNI, the
ingress/gateway, cert-manager, the secrets operator, the secret store, the GitOps controller.

> **This repo assumes a working cluster and consumes it.** A missing platform component is a
> ticket in the infra repo, never a manifest here.

_Name the infra repo here, as a path._ The reason to name it rather than say "the infra repo"
is that the sentence is read by someone deciding where to put a manifest at the moment they
are least inclined to go looking.

`requirements.yaml` is that boundary in machine-readable form: capabilities, never
implementations. *"A secret store reachable as `ClusterSecretStore/<name>`"* is a requirement;
*"deploy this particular secret manager with these values"* is the infra repo's business and
none of ours. That phrasing is what makes the boundary checkable —
`scripts/check-requirements.py` turns an unmet prerequisite into a named failure with an owner,
before deployment, instead of a `CrashLoopBackOff` an hour later that each side can blame on
the other.

**Beside — the services, owned by their own repos.** A chart ships from the service it
deploys; this repo only pins a version of it. A platform repo carrying a service's chart has
taken on something it cannot keep in step with that service's code: the chart and the code
would then be released from two repos on two schedules, and the version in the bundle would
stop meaning anything.

## Environments are directories, not branches

One cluster, one Flux instance, and the whole state diffable in a single tree. A second
cluster is a sibling directory; a second environment is a sibling directory under it.

Branch-per-environment exists elsewhere to serve two genuinely independent GitOps controllers
that must not see each other's tree. Without that constraint it only hides the diff: `dev` and
`prod` stop being comparable with `diff -r`, promotion becomes a merge with conflicts instead
of a one-line copy, and the question "what is different about prod" needs a checkout to
answer.

## Layout

```
clusters/<cluster>/environments/<env>/
  bundle.yaml            THE descriptor — what runs here, at which version
  values/common.yaml     defaults for every chart in this environment
  values/<name>.yaml     per-component overrides; the filename IS the bundle entry name
  manifests/             raw resources that are not a service chart (DB clusters, topics,
                         ExternalSecrets), one directory per component
bundle.schema.json       JSON Schema, additionalProperties: false throughout
requirements.yaml        what this platform needs from the cluster
scripts/                 validate-bundles.py · render.py · check-requirements.py
e2e/                     tier-(d) cross-service tests
```

## The bundle is the only file that carries a version

```yaml
microservices:
  - service: <service>
    repoURL: oci://<registry>/<group>/charts
    chartVersion: 0.1.3        # EXPLICIT. never a range.
```

Four rules make this safe to automate, and each one prevents a specific, seen failure:

- **`additionalProperties: false` everywhere** in the schema. A typo'd key is otherwise
  accepted, ignored, and deploys the old value — a change that reviews as done and did
  nothing.
- **`chartVersion` is exact.** Never `>=`, never `~`, never `latest`. A range means nobody can
  state what is running, and a rollback stops being a revert: reverting the bundle re-resolves
  the range to the same broken version.
- **One string, three roles.** `service` is simultaneously the chart name, the values filename
  and the generated resource name. Letting them diverge produces a values file that silently
  applies to nothing — which `validate-bundles.py` reports as a dead file precisely because it
  is invisible otherwise.
- **Comment the non-obvious.** Any tuned value carries an inline comment saying why, with the
  ticket id. A number nobody can explain is a number nobody dares change, and it outlives the
  problem it was set for.

## Rendering

`scripts/render.py` turns each bundle into Flux objects:

```
OCIRepository  flux-system/<bundle-name>-<name>   pins the chart at an exact version
HelmRelease    <namespace>/<name>                 references it via chartRef
```

The `OCIRepository` lives in the Flux namespace because the registry pull secret lives there
and is shared by every environment; its name therefore carries the bundle prefix to stay
unique across environments. The `HelmRelease` is already scoped by its namespace and does not.

Values are merged in one direction only: bundle globals → `common.yaml` → `<name>.yaml`, with
dicts merged recursively and everything else replaced. **Lists replace rather than
concatenate**, so an environment can shorten a list it inherits — with append semantics, a
value set in `common.yaml` could never be removed anywhere, only added to.

**The rendered output is never committed.** It is derived from the bundle; a committed render
is a second source of truth, and it is wrong from the moment someone edits one of the two.
CI renders on every MR and shows the diff, which is the artefact a reviewer actually reads: a
one-character `chartVersion` change is unreviewable as a bundle diff and obvious as a diff of
the rendered objects.

## Deployment model

```
service repo CI  →  publishes chart + image at one SemVer
                    writes .versions/helm-chart.env
platform repo    →  reads that file, pins chartVersion in the target environment's bundle
                    THE MERGE REQUEST IS THE DEPLOYMENT
Flux             →  reconciles from git
```

- **A service publishes; the platform pins.** The version is read from the service's committed
  `.versions/helm-chart.env`, never typed from memory — that file is generated by CI and is
  the only sanctioned crossing point between a repo and this one.
- **Promotion is a copy of a version between environment directories**, in an MR, after
  tier-(d) is green in the source environment. Never a rebuild, never a retag: the artefact
  that was tested is the artefact that moves, byte for byte.
- **Rollback is `git revert`.** If a rollback ever requires anything else, the model has been
  broken somewhere — fix that, do not work around it.
- **Bumping a version here always requires human approval.** It is a deployment, not an edit,
  and it is the smallest diff in the group with the largest effect.

## Secrets

No secret value is ever committed. Secrets are declared by *reference* and resolved in-cluster
by the External Secrets Operator against a `ClusterSecretStore`:

- **Pull from the store** for anything a human or another system provisions — registry
  credentials, third-party API keys.
- **Generate in-cluster** for anything with no external source — service-to-service tokens,
  database passwords — then push the generated value back to the store so both sides read the
  same one.
- Keys resolve as `{vaultPathPrefix}/{path}` from the bundle, so an environment's secrets are
  namespaced by construction and **a dev bundle structurally cannot read production keys**.
  That is a property of the path layout, not a permission someone has to remember to set.

See [configuration.md](configuration.md) for the per-environment values and where each
credential originates.

## CI boundary

CI **validates only — it never deploys**. Flux reconciles from git, so a pipeline that also
deployed would be a second writer to the same cluster; and a pipeline holding cluster
credentials makes every job in it, including a third-party linter, a path into the
environment. The `.gitlab-ci.yml` header states this at length so it is not quietly relaxed.

The single exception is the manual `e2e` job, which reads a real non-production environment
with a read/test-scoped kubeconfig. It deploys nothing, and the scope of that credential is
part of the design rather than an accident — see [tests.md](tests.md).

## Verification model

Tier (d) is this repo's tier (a): the cross-service tests nothing else in the group can run.
They need more than one service and a real environment, which is why every service repo's
`docs/tests.md` points here for them. See [tests.md](tests.md) and [`../e2e/`](../e2e/).

## Decisions log

Architectural decisions as `@@PREFIX@@-D<n>`: context → options → decision → consequences.
These are the decisions **no single service repo can own** — topology, contract changes,
environment shape, shared dependencies — and every participating repo cites the id from its
own ticket.

- _@@PREFIX@@-D1 — … (replace: e.g. the environment topology, or the choice to run the message
  bus in-cluster rather than as a managed service, with what it costs to reverse)._
