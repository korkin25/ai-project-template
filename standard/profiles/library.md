
---

# Profile: library

A **library** is shared code consumed by other repos as a versioned package. It builds no
image and deploys nothing. Its output is an API that other teams pin — which makes
**backwards compatibility its primary product**, ahead of any feature.

## Layout (canonical)

```
src/@@PKG@@/            the package; what is importable IS the contract
auto-tests/group-a/     tier-(a) scripts
docs/                   architecture.md, configuration.md, tests.md, contracts.md
```

There is no `deploy/` and no `helm/`. Docker and Helm jobs self-deactivate because their
marker files are absent — nothing needs disabling.

## CI

`.gitlab-ci.yml` includes `/globals.yml`, `/auto-semversioning.yml`, `/lint.yml`, `/sast.yml`,
plus a publish job gated on the release branches. Pin `ref:` to a tag.

## The public API is the contract

- **Everything exported from `src/@@PKG@@/` is public** unless it is prefixed with `_`.
  There is no "internal but importable" — if a consumer can import it, it is a contract.
- `docs/contracts.md` lists every exported symbol other repos rely on. A symbol that is
  removed or has its meaning changed is a **breaking change**, which is an architectural
  decision requiring user approval.
- **SemVer is a promise, not a formality.** Patch: fixes only. Minor: additive only. Major:
  anything a consumer must react to.
- **Deprecate before removing.** Ship the replacement, mark the old symbol deprecated with
  the version that will remove it, give consumers a release to move, then remove.

## Dependencies

A library's dependencies become every consumer's dependencies. Keep the required set
minimal and put anything a subset of consumers needs behind an **optional extra**, so a
service that only produces messages does not inherit a vector-database client.

Declare version ranges, not pins — a library that pins exact versions makes itself
un-composable with anything else.

## Release and the consumer bump

1. Merge to `rc`/`release` → CI publishes the package at `GitVersion_SemVer`.
2. **Consumers do not update themselves.** Open a ticket in each consuming repo referencing
   the platform id; each bumps its own pin, on its own branch, verified by its own CI.
3. Never edit another repo's pin yourself.

Because every consumer must move for a breaking change, batch such changes: a library that
cuts a major version twice in a month has made the whole platform unmovable.

## Published artifacts

- Python package → the group PyPI registry. Consumers pin with a compatible-release
  specifier (`~=X.Y`) and install through the group index.
