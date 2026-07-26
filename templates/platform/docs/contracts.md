# Contracts — @@PROJECT@@

A **contract** is anything one repo depends on from another: a message topic and its schema, a
database table, an HTTP or MCP endpoint, a symbol exported from a published library, a chart
name, a capability the cluster must provide.

**This file is the registry.** Every other repo keeps the local half — what *it* owns and what
*it* consumes; this is the system-wide view, and it is the file that answers *"who consumes
this topic?"* when a service repo asks before changing it. Every service repo's
`docs/contracts.md` points here for that answer, so a gap in this table is not a documentation
gap — it is a producer who will make a breaking change believing nobody was listening.

Keeping it accurate is the whole of the *Cross-repo contracts* protocol. Without it the
protocol has nothing to stand on: step 1 is "find out who depends on it", and an incomplete
table answers that question wrongly rather than admitting it cannot.

## The registry — contracts between repos

One row per contract, not per repo. **The consumer list is the blast radius** of any change to
it, and the tier-(d) column is what would actually catch a break.

| Contract | Shape | Owner (repo) | Consumers | Tier-(d) test |
|---|---|---|---|---|
| _e.g. `<topic>` messages_ | _envelope + payload schema, from the shared library_ | _`<producer-repo>`_ | _`<consumer-repo>`, `<consumer-repo>`_ | _`e2e/<name>.sh`_ |
| _e.g. `<endpoint>`_ | _HTTP, request/response shape_ | _`<repo>`_ | _`<repo>`_ | _—_ |
| _e.g. `<table>`_ | _schema, owned changelog_ | _`<repo>`_ | _`<repo>`_ | _—_ |

A contract with no tier-(d) test is not a defect on its own — some are covered adequately by
the producer's own suite. A contract with no tier-(d) test **and** more than one consumer is a
gap worth a ticket: nothing in the group is checking that the two consumers still agree.

## Owned by this repo

| Contract | Consumed by | Breaking it looks like |
|---|---|---|
| **Environment names and namespaces** (`clusters/<cluster>/environments/<env>/`) | every service repo's docs, dashboards, runbooks, the infra repo's namespace list | A renamed environment orphans its secret-store prefix and every URL derived from the namespace. Nothing fails at merge time; the next reconcile deploys a *second* copy under the new name. |
| **`bundle.schema.json`** | `render.py`, `validate-bundles.py`, any tooling reading a bundle | `additionalProperties: false` is load-bearing: relaxing it turns a typo from a CI failure into a silent no-op deployment. |
| **`requirements.yaml`** | the infra repo — it is a standing demand on another team | Adding a `required: true` entry makes every cluster non-compliant until that team acts. That is a ticket in their repo before it is a line here. |
| **Platform ids `@@PREFIX@@-<n>` / `@@PREFIX@@-D<n>`** | every repo in the group cites them | Renumbering or reusing an id invalidates citations in repos nobody is looking at. Ids are sequential and never reused. |
| **`.versions/*.env` as an input format** | specified in the standard, produced by each service repo's CI | This repo *reads* those files; a service that stops writing them cannot be deployed by anything but hand-typed versions. |

## Consumed by this repo

Everything here is pinned, and each pin is somewhere a script can read it.

| Contract | Owner | Pinned at | Used for |
|---|---|---|---|
| Service charts | each service repo | `chartVersion` in each bundle — **exact, never a range** | what is deployed |
| Service images | each service repo | the chart's `appVersion`, which equals the chart version | what runs |
| `.versions/helm-chart.env` | each service repo | read at deploy time; never cached here | the version to pin |
| Third-party charts (bus, database, vector store) | upstream vendors | `chartVersion` under `platform:` in each bundle | the data plane |
| Cluster capabilities | the infra repo | `requirements.yaml`, checked by `check-requirements.py` | everything works at all |
| Flux APIs (`OCIRepository`, `HelmRelease`) | upstream | the `apiVersion` written by `render.py` | a controller upgrade that drops an API version stops reconciliation **silently** |
| Shared CI templates | `@@CI_TEMPLATES_PROJECT@@` | `ref:` in `.gitlab-ci.yml` | the validate pipeline |

## Changing a contract

The protocol is in `CLAUDE.md` under *Cross-repo contracts*; what this repo adds is that
**this is where it is coordinated**.

1. **Open `@@PREFIX@@-D<n>` here** — what changes, who consumes it today (the table above),
   whether the change is compatible, and the migration path. A breaking change is
   architectural and **requires the user's approval**.
2. **Prefer additive.** Add a field, a topic, a version suffix; never repurpose one. A consumer
   you forgot about must keep working — and the table above is a list of the ones you
   remembered.
3. **Producer first, then consumers, then remove.** Merge order is library → producing service
   → consuming service → **this repo's bundle**. Merging out of order breaks the consumer for
   exactly as long as the gap lasts.
4. **Open the consumer tickets yourself**, one per affected repo, each citing the `@@PREFIX@@`
   id. An unannounced contract change is the most expensive mistake available across repos.
5. **Update the tier-(d) test in the same change set.** A contract change in any service repo
   updates the matching test *here* — that is the rule the whole tier exists for, and the one
   most often deferred into never.
6. **Update this table on both sides**, in the same change as the bundle bump that lands it.

## Frozen and legacy

Repos that are read-only, contracts kept alive for a single consumer, versions pinned because
an upgrade is blocked — record them here with the reason and the ticket. A frozen repo is
never modified without an explicit instruction naming it, and the only way anyone knows it is
frozen is this table.

| Repo / contract | State | Why | Ticket |
|---|---|---|---|
| _none_ | | | |
