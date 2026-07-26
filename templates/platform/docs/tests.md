# Test plan — @@PROJECT@@

**Tier (d) is this repo's centre of gravity**, which inverts the usual shape of this file.
Every other repo in the group writes tier (d) as "lives in the platform repo, not here" —
this is that repo. Nothing else in the group can run a test that needs two services and a real
environment, so a tier-(d) test that is not written here is not written anywhere.

| Tier | Here | Why |
|---|---|---|
| **(a) fully automated** | The CI pipeline: `yamllint`, `validate-bundles`, `render-diff`, gitleaks, checkov. | These are the only checks that need no cluster. CI holds no deploy credential, so it proves a bundle is *well-formed and renders*, never that it *works*. |
| **(b) dev-machine / sandbox** | `check-requirements.py` against a real cluster, `render.py` diffed against what is live, a reconcile watched to completion. See [`../auto-tests/group-b/`](../auto-tests/group-b/). | Needs real access. Run by the agent in a sandbox, and by a human reading the diff before merging. |
| **(c) human-in-the-loop** | Promotion and rollback drills, a first deploy into a shared environment. See [`../auto-tests/group-c/`](../auto-tests/group-c/). | Someone has to decide the environment is *right*, not merely reconciled. |
| **(d) cross-service e2e** | [`../e2e/`](../e2e/) — **owned here**. | They prove the services work *together*, which no service repo can do alone. |

There is no `auto-tests/group-a/` in this repo, and that absence is deliberate: tier (a) here
is the pipeline itself, and a directory of scripts that merely re-ran what CI already runs
would be a second thing to keep in step.

A task is done only when **100 %** of its applicable tiers pass; per-test status for the work
currently in progress is tracked in [../TODO.md](../TODO.md).

## Tier (a) — what CI proves on every merge request

| Check | What it asserts | Status |
|---|---|---|
| `yamllint` | No duplicate keys, no implicit octals, no accidental booleans — the quirks that silently change meaning in a file a controller reads | ✅ |
| `validate-bundles` | Every bundle matches `bundle.schema.json` (`additionalProperties: false`), plus what a schema cannot express: a name used twice, an unreferenced values file, an environment directory whose name is missing from its bundle name, two environments sharing a namespace | ✅ |
| `render-diff` | Every bundle renders to Flux objects, every object is addressable, and every `HelmRelease` points at an `OCIRepository` that was actually emitted. The diff against the merge base is printed for the reviewer | ✅ |
| gitleaks | No secret value committed — the assumption the entire secrets model rests on | ✅ |
| checkov | No permissive defaults in the raw resources under `clusters/**/manifests/` | ✅ |

**What tier (a) explicitly does NOT prove:** that the deployment works. Nothing is applied, so
a green pipeline means "this is a valid statement about what should run". Treating it as
approval to promote is the mistake this table exists to prevent.

## Tier (d) — the cross-service suite

Scenarios live in [`../e2e/`](../e2e/); this table is their catalogue and their status.

| Test | Contract it exercises | Owner of that contract | Status |
|---|---|---|---|
| _e.g. `e2e/ingest-to-query.sh`_ | _`<topic>` → `<endpoint>`_ | _`<repo>` → `<repo>`_ | ⬜ |

Three rules that keep the tier honest:

- **Each test names the contract it exercises**, so a failure points at an owner rather than
  at "the system". A red suite that nobody owns gets muted, and a muted suite is worse than an
  absent one because it still looks like coverage.
- **A contract change in any service repo updates the matching test here, in the same change
  set** — a separate MR in this repo, linked by the `@@PREFIX@@` id. Deferred, it becomes a
  test asserting a contract that no longer exists, and the next person deletes it rather than
  fixing it.
- **They run against a real cluster, never a mock.** A local k3s is a legitimate target and is
  the default for development. Mocking the other service is how two repos stay green while
  disagreeing about the same field.

**E2E is a promotion gate**: green in the source environment before a version moves onward.
The CI job is manual and non-blocking on purpose — the enforcement is that the promotion MR
states which run was green, because a blocking manual job only teaches people to click it.
See [`../e2e/README.md`](../e2e/README.md).

## Tier (b) — before every merge that changes an environment

Merging is the deployment, so this is the last point at which a human sees the change before
the cluster does.

| Check | Command | Records |
|---|---|---|
| The bundle is valid | `python3 scripts/validate-bundles.py` | the summary line |
| It renders to what you expect | `python3 scripts/render.py --all` | the rendered objects, skimmed |
| The cluster can host it | `python3 scripts/check-requirements.py --context <cluster>` | the report, including `UNVERIFIED` rows |
| The delta against what is live | `flux diff kustomization <name> --path <path>` | the diff, in the MR |
| It converges | `flux get kustomizations -A`, then the workload's own health | the read-back |

`check-requirements.py` reports data services as `UNVERIFIED` rather than guessing: "a
Kafka-compatible bus" may be an operator, a chart or a managed endpoint, and probing for one
implementation would report a confident false failure for the other two. An `UNVERIFIED` row
is a question for a human, not a pass.

## Tier (c) — promotion, rollback, and first deploys

| Methodology | Why a human |
|---|---|
| Promotion drill: move one version between environments, following the real process | Proves the process, not the tooling. The step people skip is the tier-(d) check, and only a human notices they skipped it. |
| Rollback drill: `git revert` a bundle bump and confirm the previous version returns, timed | A rollback nobody has ever performed is a hypothesis, and it is tested for the first time during an incident. |
| First deploy of a new service into a shared environment | Someone must confirm the version reported by the running service is the one that was released. |

## Recording results

Every verification is recorded in `AUTOPILOT-LOG.md` under **Verified by**, with the real
output. "Merged successfully" is not verification — merging only starts the reconcile:

```
flux get kustomizations -A
kubectl -n <namespace> get helmrelease
kubectl -n <namespace> get pods
```

<!-- Template — copy per new feature or contract change:

## <feature or contract> — <@@PREFIX@@-n>

| Test | Tier | What it asserts | Status |
|---|---|---|---|
| … | (a) | … | ⬜ |
| … | (b) | … | ⬜ |
| … | (c) | methodology proposed to the user | ⬜ |
| `e2e/…` | (d) | … (name the contract and its owner) | ⬜ |
-->
