# Configuration — @@PROJECT@@

**A library reads no configuration.** There is no runtime environment to configure: every
value comes in as an argument from the application that imports it.

That is a design rule, not an accident of this being a young repo. A library that reads
`os.environ` at import time is configured by whichever service imported it first, cannot be
tested twice in one process with different settings, and turns a missing variable into an
`ImportError` in someone else's service — three failure modes the consumer cannot fix
without forking.

If something *feels* like library configuration, it is one of these instead:

| Feels like | Actually is | Where it goes |
|---|---|---|
| "the broker URL" | application configuration | the consuming service's `docs/configuration.md` |
| "the default timeout" | a function argument with a default | the API, and therefore `docs/contracts.md` |
| "the log level" | the application's logging setup | the consumer; this library only ever calls `logging.getLogger(__name__)` and never configures handlers |
| "which backend to use" | an optional extra plus an explicit factory argument | `pyproject.toml` extras + `docs/contracts.md` |

## Environment used by the toolchain

These affect building and publishing, never runtime behaviour of the package:

| Variable | Where | Purpose |
|---|---|---|
| `CI_JOB_TOKEN` | CI only | Authenticates `twine upload` to the group registry. Short-lived, never stored. |
| `PIP_EXTRA_INDEX_URL` | dev / CI | Authenticated group index, so group-internal packages resolve. Contains a token — never commit it, never echo it. |

## Installing this library

```bash
pip install '@@PROJECT@@~=0.1' --extra-index-url "${PIP_EXTRA_INDEX_URL}"
```

A compatible-release pin takes patches automatically and never a minor with new API surface.
