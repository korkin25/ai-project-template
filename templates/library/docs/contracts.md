# Contracts — @@PROJECT@@

**This file is the exported-symbol registry, and it is enforced.**
`tests/test_public_api.py` fails the build when a name in `@@PKG@@.__all__` is missing from
this document, and when a public module-level name is missing from `__all__`. The registry
therefore cannot drift — which is the only thing that makes it worth reading.

For a library the public API *is* the product: everything importable without a leading
underscore is a promise. Backwards compatibility outranks any feature, because every
consumer must move for a breaking change, and they move on their own schedule.

## Compatibility rules

| Change | Version bump | Approval |
|---|---|---|
| Fix that keeps behaviour | patch | normal review |
| New symbol, new optional argument, new payload field | minor | normal review |
| Removing/renaming a symbol, changing a meaning, tightening a type | **major** | **architectural — user approval required** |

**Deprecate before removing.** Ship the replacement, mark the old symbol with the version
that will remove it (`Deprecated since X.Y, removed in Z.0`), give consumers at least one
release to move, then remove it. And **batch** breaking changes: a library that cuts a major
twice in a month makes the whole platform unmovable, because every consumer repo has to
spend a branch on each.

## Exported symbols

Every row here is something another repo may rely on. Nothing outside this table is a
contract — behaviour that merely happens to work is not a promise, and asking for it is a
ticket in this repo rather than an assumption in theirs.

| Symbol | Kind | Signature / shape | Since | Stability |
|---|---|---|---|---|
| `__version__` | constant | `str`, PEP 440, written by CI at publish time | 0.1.0 | stable |
| `Envelope` | frozen dataclass | `key: str`, `payload: dict[str, Any]`, `schema_version: int = 1`, `emitted_at: datetime` (tz-aware UTC) | 0.1.0 | stable |
| `Envelope.to_dict` | method | `() -> dict[str, Any]` — JSON-compatible; `emitted_at` as ISO-8601 | 0.1.0 | stable |
| `Envelope.from_dict` | classmethod | `(dict[str, Any]) -> Envelope`; raises `ValueError` on anything malformed | 0.1.0 | stable |
| `new_envelope` | function | `(key: str, payload: dict[str, Any], schema_version: int = 1) -> Envelope` | 0.1.0 | stable |

## Payload schema evolution

`Envelope.schema_version` is what keeps the wire format evolvable without a flag day:

1. Add fields, never repurpose them, and leave the version alone — old consumers ignore what
   they do not know.
2. A change consumers must react to bumps `schema_version` **and** ships producers emitting
   both shapes.
3. Move every consumer, then remove the old shape. Never invert that order.

## Consumers

Track who depends on this library, so a proposed break has a known blast radius and the
consumer tickets can actually be opened. Keep it current — an unlisted consumer is one that
gets broken.

| Repo | Pins | Uses |
|---|---|---|
| _none yet_ | | |

## Consuming this library

```
@@PROJECT@@~=X.Y     # compatible-release: picks up patches, never a minor with new API
```

installed from the group index. Consumers do **not** update themselves: when a new version
ships, open a ticket in each consuming repo (citing the platform id) and let each bump its
own pin on its own branch, verified by its own CI. Never edit another repo's pin yourself.
