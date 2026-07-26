# Architecture — @@PROJECT@@

> **Design-before-code lives here.** No implementation — not even tests — starts until the
> design is written down: the public API, its compatibility story, and the trade-offs
> against the alternatives that were rejected. For a library, "the design" is mostly *the
> shape of the API*, because that is the part that cannot be changed later without every
> consumer paying for it. Anything that changes a published symbol is architectural by
> definition and needs the user's approval.

## Overview

<What this library provides and to whom. One sentence on what would have to be duplicated in
every service if it did not exist — that is the test of whether it should.>

## Scope

A library holds **shared code and cross-service contracts**. Two boundaries are worth
stating explicitly, because the drift is gradual and nobody notices until it hurts:

- **No I/O policy.** Types, serialisation and pure helpers travel well; retry policies,
  connection pools and "our standard client" do not — a service that cannot choose its own
  timeouts will eventually vendor a copy of this library instead of pinning it.
- **No configuration.** Reading the environment is the application's job. A library that
  reads `os.environ` at import time is untestable in every consumer at once.

## Modules

| Module | Responsibility | Public? |
|---|---|---|
| `@@PKG@@/__init__.py` | The public surface: re-exports everything consumers may use. | yes |
| `@@PKG@@/_…` | Internal helpers, underscore-prefixed so they are not importable contracts. | no |

New modules re-export their public names from `__init__.py`. Consumers then have exactly one
import path to pin, and reorganising internals stops being a breaking change.

## Compatibility model

SemVer here is a promise, not a formality: patch = fixes, minor = additive only, major =
anything a consumer must react to. The mechanics — deprecation windows, the enforced symbol
registry, the schema-version rule — are in [contracts.md](contracts.md).

## Dependencies

Required dependencies are the ones every consumer inherits, so the required set is kept
minimal and anything a subset needs goes behind an optional extra. Ranges, never pins (see
`pyproject.toml` for why a pinned library is un-composable).

## Release shape

```
commit ──► CI (version, lint, type, test, scan) ──► merge to rc/release ──► group PyPI registry
                                                                              │
                                       consumers bump their own pin, in their own repo, on
                                       their own branch, verified by their own CI
```

No image, no chart, no deployment. The only artifact is the package.

## Decisions log

Architectural decisions as `@@PREFIX@@-D<n>`: context → options → decision → consequences.
A decision that changes a published symbol also gets a platform-level id and a ticket in
every consuming repo.

- _@@PREFIX@@-D1 — … (replace: e.g. why the envelope is frozen, or why serialisation is
  hand-rolled rather than pulled from a framework)._
