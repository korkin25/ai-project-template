# @@PROJECT@@

@@DESCRIPTION@@

Shared code consumed by other repos as a versioned package, following the **library** profile
of the shared standard (`standard/profiles/library.md`). It builds no image and deploys
nothing: its output is an API that other teams pin, which makes **backwards compatibility
its primary product** — ahead of any feature.

| | |
|---|---|
| Package | group PyPI registry — `pip install '@@PROJECT@@~=0.1'` |
| Import | `import @@PKG@@` |
| Contract | [`docs/contracts.md`](docs/contracts.md) — the enforced registry of every export |
| Rules | [`CLAUDE.md`](CLAUDE.md) — generated from `standard/` |

## Features

> User-facing features only — what this library gives the teams that import it. Engineering
> and infrastructure work belongs in [`CHANGELOG.md`](CHANGELOG.md), ideas in
> [`TODO.md`](TODO.md). A feature lands here **when it ships**.

- **Message envelope.** `Envelope` / `new_envelope` give every service the same wire format
  — an idempotency key, a timezone-aware UTC timestamp, and an explicit `schema_version` so
  the payload can evolve without a flag day.
- _Add the next shipped capability here._

## Adopting this scaffold

1. Replace every placeholder: `@@PROJECT@@` (hyphenated package/repo name), `@@PKG@@`
   (underscored Python package, also the `src/@@PKG@@/` directory), `@@PREFIX@@` (ticket
   prefix), `@@GROUP@@` (GitLab namespace), `@@DESCRIPTION@@`, `@@CI_TEMPLATES_PROJECT@@`
   (the shared CI templates repo, as a GitLab project path), `@@CI_TEMPLATES_REF@@` (the tag
   of it to pin) and `@@RUNNER_TAG@@` (the tag of your runner fleet — it appears in three
   blocks of `.gitlab-ci.yml` that must stay in sync).
   `grep -rnE '@{2}' .` must come back empty.
2. Run `./standard/compose.sh` to generate `CLAUDE.md`, and commit it.
3. Set `next-version` in `GitVersion.yml` to the first version you intend to publish.
4. Replace the sample `Envelope` with the real API — and update `docs/contracts.md` in the
   same change, because the test suite enforces that they agree.

## Layout

```
src/@@PKG@@/          the package — what is importable IS the contract
tests/                the tier-(a) suite; for a library this is all of tier (a)
auto-tests/           tier-(b)/(c) material; group-a stays empty (see its README)
docs/                 architecture, configuration, tests, contracts
standard/             the shared rulebook's sources + this repo's identity
```

There is no `deploy/` and no `helm/`. The Docker and Helm jobs in the shared CI templates
self-deactivate because their marker files are absent — nothing needs disabling, and adding
either one silently turns this repo into something else.

## Local development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'

pytest                 # includes the contract-registry checks
ruff check src tests
mypy src tests
```

## Publishing

Publishing is a **merge**, not a tag: `rc` publishes a pre-release, `release` publishes the
stable version, and both are approval-gated. CI computes the version with GitVersion,
translates it to PEP 440, writes it into the package and uploads to the group registry.

Publication is **irreversible** — the registry refuses re-uploads of a version, so a bad
artifact must be superseded, never replaced. That is why nothing publishes from `dev` or from
a feature branch.

## For consumers

```
@@PROJECT@@~=X.Y
```

Pin with a compatible-release specifier and rely only on what `docs/contracts.md` documents.
**Consumers do not update themselves**: when a new version ships, each consuming repo bumps
its own pin on its own branch, verified by its own CI, tracked by its own ticket.
