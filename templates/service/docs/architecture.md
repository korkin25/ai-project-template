# Architecture — @@PROJECT@@

> **Design-before-code lives here.** No implementation — not even tests — starts until the
> design for a task is written down: the data model, the public API/contract, the deployment
> shape, the components touched, and the trade-offs against the alternatives that were
> rejected. For a trivial change that may be one sentence, but it is still written first.
> Any architectural decision needs the user's approval, and anything that changes a
> cross-repo contract is architectural by definition.

## Overview

<What this service does, in three sentences: what it consumes, what it produces, and what
would break if it stopped.>

## Components

| Component | Responsibility |
|---|---|
| `src/@@PKG@@/main.py` | Process lifecycle: config, health endpoint, intake loop, shutdown. |
| `src/@@PKG@@/…` | <the actual work — add rows as modules appear> |
| `helm/` | How the process is deployed: hardening, probes, resources, routing. |
| `deploy/Dockerfile` | How the process is packaged: non-root, read-only-rootfs-ready. |

## Runtime model

The process is a worker with a health endpoint, not an HTTP server that also works:

- **Intake → process → commit.** The commit happens only after the work succeeded, so a
  crash costs a redelivery instead of a lost message. `handle_message` must therefore be
  idempotent — at-least-once delivery guarantees it will eventually run twice on the same
  key.
- **Shutdown.** SIGTERM closes intake, the in-flight batch is finished and committed, the
  process exits 0. The chart's `terminationGracePeriodSeconds` is the budget for that.
- **Health.** `GET /health` always answers 200; the body's `status` distinguishes `ok` from
  `draining`, and `version` reports the released SemVer that the chart injected.

## Data model

<The source of record, its storage, its schema, and what is derived and therefore
rebuildable. If this service owns no state, say so explicitly — "stateless, all state lives
in X" is a design statement, not an omission.>

## Public interfaces / contracts

Everything another repo depends on is listed in [contracts.md](contracts.md) and must be
changed through the protocol described there. This section describes them; that file is the
registry.

## Deployment shape

One commit produces one image and one chart, at the same `GitVersion_SemVer`:

```
commit ──► CI ──► image  <registry>/@@GROUP@@/@@PROJECT@@:<SemVer>
                └► chart oci://<registry>/<group>/charts/@@PROJECT@@:<SemVer>
                                              │
                          platform repo bundle.yaml pins chartVersion
                                              │
                                     Flux reconciles ──► namespace
```

This repo's pipeline stops at "published". **Deployment is a reviewed MR in the platform
repo** that bumps `chartVersion` for one environment. The reasons are worth restating,
because the shortcut is always tempting: only the platform repo can know which versions are
compatible with each other in a given environment, a deploying pipeline would need
cluster-admin credentials in every service repo, and a rollback must be a revert of a
reviewed change rather than a re-run of a job.

Runtime configuration is in [configuration.md](configuration.md). The chart carries defaults
only; per-environment values live in the platform repo.

## Decisions log

Architectural decisions as `@@PREFIX@@-D<n>`, ADR-style: context → options → decision →
consequences. A decision that changes a cross-repo contract also gets a platform-level id.

- _@@PREFIX@@-D1 — … (replace: the first real decision, e.g. the choice of message source)._
