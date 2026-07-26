# Test plan — @@PROJECT@@

Per-feature test catalog. When a feature is picked up — after its design is fixed, **before**
any code — add its section here with the concrete tests, each tagged by tier. See the Testing
policy in [../CLAUDE.md](../CLAUDE.md).

- **(a) Fully automated** — the `tests/` suite, run in CI by the shared Python gate
  (`/lint.yml`: ruff + mypy + pytest on 3.11 and 3.12). For a library this is the whole of
  tier (a): there is no image to boot, so `/functional.yml` is not included and
  `auto-tests/group-a/` stays empty by design (see [`../auto-tests/README.md`](../auto-tests/README.md)).
  The agent reads the run logs even when green.
- **(b) Dev-machine / AI-sandbox** — installing the built wheel into a clean environment and
  importing it, or running a consumer's suite against a pre-release. Needs a registry and a
  scratch venv, so it is not a CI gate.
- **(c) Human-in-the-loop** — a review of the API shape before it becomes permanent. Cheaper
  than any amount of testing after publication, because publication is irreversible.
- **(d) Cross-service end-to-end** — lives in the **platform repo**. This repo's obligation
  is to keep its half testable: stable exports, a documented schema, and a version consumers
  can pin.

A task is done only when 100 % of its applicable tiers pass; per-test status for the feature
in progress is in [../TODO.md](../TODO.md).

---

## Baseline — the public API is the product

| Test | Tier | What it asserts | Status |
|---|---|---|---|
| `tests/test_public_api.py::test_all_is_sorted_and_importable` | (a) | every promised export exists | ✅ |
| `tests/test_public_api.py::test_every_public_symbol_is_documented` | (a) | every export is in `docs/contracts.md` — the registry cannot drift | ✅ |
| `tests/test_public_api.py::test_no_accidental_exports` | (a) | no public module-level name escaped `__all__` | ✅ |
| `tests/test_public_api.py::test_public_symbols_are_typed_and_documented` | (a) | every export carries a docstring | ✅ |
| `tests/test_public_api.py::test_envelope_round_trips` | (a) | `to_dict`/`from_dict` are inverses | ✅ |
| `tests/test_public_api.py::test_from_dict_rejects_a_malformed_message` | (a) | malformed input fails loudly instead of half-parsing | ✅ |
| Install the built wheel into a clean venv and import it | (b) | the published artifact is usable, not just the source tree | ⬜ |

<!-- Template — copy per new feature:

## Feature <n> — <title>

| Test | Tier | What it asserts | Status |
|---|---|---|---|
| … | (a) | … | ⬜ |
| … | (b) | … | ⬜ |
| … | (c) | API review proposed to the user | ⬜ |
| platform repo: … | (d) | … (link the platform id) | ⬜ |
-->
