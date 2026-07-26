# Contracts — @@PROJECT@@

A **contract** is anything outside this repo depends on: a message topic and its schema, a
database table this service writes, an HTTP or MCP endpoint, a published symbol. This file
is the local half of the registry; the platform repo holds the system-wide view. **It is the
file that must never go stale** — a consumer reads it instead of reading this repo's source,
and everything it does not describe is something they were never promised.

## Owned by this repo

Other repos may depend on these. Changing one follows the protocol below.

### HTTP

| Endpoint | Method | Response | Consumers |
|---|---|---|---|
| `/health` | `GET` | `200` + `{"status": "ok"\|"draining", "version": "<semver>"}` | the chart's probes; the platform's tier-(d) tests |

### Messages / topics

| Topic | Direction | Key | Payload schema | Consumers |
|---|---|---|---|---|
| _none yet_ | | | | |

### Storage

| Table / collection | Written by | Read by | Notes |
|---|---|---|---|
| _none yet_ | | | |

## Consumed from other repos

Pin the version you tested against, and rely only on what the owning repo's
`docs/contracts.md` actually documents. Behaviour you observed but nobody promised is not a
contract — needing it is a request to that repo, not an assumption.

| Contract | Owner repo | Version pinned | Used for |
|---|---|---|---|
| _none yet_ | | | |

## Changing a contract you own

1. **Design it as a platform decision.** Open `<PLATFORM>-D<n>` in the platform repo: what changes,
   who consumes it today, whether it is compatible, and the migration path. A breaking
   change is an architectural decision and **requires the user's approval**.
2. **Prefer additive.** Add a field; do not repurpose one. Add a topic or a version suffix;
   do not quietly change what a payload means. A consumer you forgot about must keep working.
3. **Producer first, then consumers, then remove.** Emit both shapes, move every consumer,
   only then delete the old one. Never invert that order.
4. **Open the consumer tickets yourself**, one per affected repo, each citing the platform
   id. An unannounced contract change is the most expensive mistake available here.
5. **Update this file on both sides**, in the same change as the code, and update the
   tier-(d) test in the platform repo.
