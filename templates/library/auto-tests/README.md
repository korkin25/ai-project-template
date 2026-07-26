# auto-tests — tiers (b) and (c)

The tier doctrine is the same as everywhere else in the standard, but a library maps onto it
differently, and the difference is worth writing down so nobody "fixes" it:

| Tier | Where it lives here | Why |
|---|---|---|
| (a) fully automated | `tests/` (pytest), run by `/lint.yml` | There is no image to boot, so `/functional.yml` is not included in this repo's CI. A `group-a/*.sh` script placed here would therefore **never run** — a test that silently does not execute is worse than no test. |
| (b) dev-machine / sandbox | `group-b/` | Needs a registry, a scratch venv, or a consumer's suite. |
| (c) human-in-the-loop | `group-c/` | API review before publication — the one review that cannot be repeated afterwards. |
| (d) cross-service e2e | the **platform repo** | Needs more than one repo and a real environment. |

## group-b — dev-machine / AI-sandbox

The scenarios worth having for a library:

- **Install the built wheel into a clean virtualenv and import it.** Catches the whole class
  of "works from the source tree" bugs: a package missing from the wheel, a module that only
  resolves because `src/` happened to be on `sys.path`, a missing runtime dependency that the
  dev extra was quietly providing.
- **Run a real consumer's test suite against the pre-release.** The cheapest possible
  detection of a break that the type checker cannot see.
- **Import time and dependency tree** (`pip install` into an empty venv, then inspect it):
  every dependency here is inherited by every consumer.

Same exit contract as tier (a) — `0` pass, `77` skip, anything else fail — so a scenario can
be promoted by moving the file if this repo ever gains a functional job.

## group-c — human-in-the-loop

Chiefly **API review**: a name, a default, or a return type is permanent the moment it is
published, and no automated test has an opinion about whether an API is good. Write the
methodology (what changed, who consumes it, what the alternative shapes were) and hand it to
the user before the merge to `rc`.
