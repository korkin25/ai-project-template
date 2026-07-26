# Environments — @@PROJECT@@

The inventory of every environment this repo deploys, and the rules that differ between them.
**An environment that is not in this table is one whose rules nobody knows**: who may approve a
deployment into it, whether it holds real data, and what it is allowed to be used for.

Environments are **directories, not branches** — one tree, diffable end to end. A second
cluster is a sibling of `clusters/<cluster>/`; a second environment is a sibling of
`environments/<env>/`.

## Inventory

| Environment | Cluster | Namespace | Secret prefix | Real data | Deployment approved by | Purpose |
|---|---|---|---|---|---|---|
| `dev` | `<cluster>` | `<platform>` | `dev` | no | any maintainer | integration; the first target of every version |
| _`stage`_ | _…_ | _…_ | _`stage`_ | _copy_ | _…_ | _pre-production verification_ |
| _`prod`_ | _…_ | _…_ | _`prod`_ | _yes_ | _named humans_ | _the one that matters_ |

Fill this in as environments are created, and keep the "approved by" column honest — it is the
only place that answers "may I merge this bundle bump" without asking in chat.

Two invariants the tooling enforces, so they cannot rot silently:

- **The bundle `name` contains the environment directory name.** Promotion is a copy between
  directories, and that correspondence is what makes it verifiable.
- **No two environments share a namespace.** They would render `HelmRelease`s with identical
  names into the same place and overwrite each other. `validate-bundles.py` checks this across
  files, which a JSON Schema cannot.

## The promotion path

```
dev  →  stage  →  prod          (a copy of a version, never a rebuild)
```

- **Promotion is a copy of an exact version between environment directories**, in an MR, after
  tier-(d) is green in the source environment. Never a rebuild, never a retag: the artefact
  that was tested is the artefact that moves, byte for byte. A rebuild "from the same commit"
  is a different artefact — different base image, different transitive dependencies, different
  timestamp — and it has been tested nowhere.
- **Forward only.** A version that is in `prod` and not in `stage` means someone skipped a
  step, and the environments have stopped being comparable.
- **The MR states which tier-(d) run was green**, with its output or its job id. That sentence
  is the gate; the CI job is manual precisely because a blocking button gets clicked rather
  than read.
- **Every promotion requires human approval.** It is a deployment, not an edit.

## What differs between environments, and what must not

| Differs | Must not differ |
|---|---|
| Versions (that is the whole point of separate bundles) | The chart — the same chart is deployed everywhere, configured differently |
| Replica counts, resource requests, retention windows | The way secrets are resolved — every environment uses the store, none has a committed value |
| `publishDomain`, `vaultPathPrefix`, namespace | The shape of the tree — a differently-structured environment cannot be diffed against its neighbour |
| Which optional components are enabled | The rule that `chartVersion` is exact |

The right-hand column is the one that pays off during an incident: when `prod` misbehaves and
`stage` does not, the useful question is "what is different", and it is only answerable if the
answer is short.

## Per-environment notes

### `dev`

The first target of every version, and the only environment where a maintainer may approve
their own bundle bump. It holds no real data, which is what makes that safe — and the day it
does hold real data, this row changes and so does the approval rule.

### _`stage`_ / _`prod`_

_Add a section per environment as it is created. Each one records: what it is for, what data
it holds, the approval rule, and anything an operator must know before touching it (a
maintenance window, a data-retention obligation, a paging rotation)._

## Adding an environment

The mechanics are in [configuration.md](configuration.md). What belongs *here* is the row in
the inventory above plus a section saying who may deploy into it and what it is for — written
in the same change that creates the directory, because an environment appears in the tree the
moment its bundle exists, and from then on somebody can deploy into it.

## Deleting an environment

Delete the directory, and in the same change: remove the row above, note the removal in
`CHANGELOG.md`, and open a ticket in the infra repo for the namespace and the secret-store
prefix. **Deleting the directory does not delete the environment** — it stops the reconciler
managing it, which leaves a namespace full of workloads nobody is now watching. That is a
worse state than either having it or not.
