"""@@PROJECT@@ — @@DESCRIPTION@@.

**What is importable from here IS the contract.** Everything exported without a leading
underscore is public: there is no "internal but importable" tier, because a consumer that
can import a symbol will import it, and the next release that changes it breaks their build.

Rules this module lives by (standard/profiles/library.md):

* every public symbol is listed in ``__all__`` AND in ``docs/contracts.md`` — the test suite
  fails if the two disagree, so the registry cannot silently rot;
* removing a symbol, or changing what it means, is a **breaking change** — an architectural
  decision that needs the user's approval and a major version;
* deprecate before removing: ship the replacement, mark the old symbol with the version that
  will delete it, give consumers a release to move, then remove;
* new modules re-export their public names here, so consumers have exactly one import path
  to pin and internal reorganisation is not a breaking change.

Consumers install from the group PyPI registry and pin with a compatible-release specifier
(``@@PROJECT@@~=X.Y``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# The public surface, in one place. A symbol not listed here is not published — and the
# suite enforces that a module-level name defined in this package is either private
# (leading underscore) or listed, so a helper cannot become an accidental contract by
# sitting in the wrong file.
__all__ = ["Envelope", "__version__", "new_envelope"]

# Overwritten by CI at publish time (`hatch version <PEP 440>`, see .gitlab-ci.yml) from
# GitVersion_SemVer. Never hand-edit it: the number here would then disagree with the
# version the registry serves, and a consumer debugging behaviour would be reading the
# wrong source.
__version__ = "0.0.0"


@dataclass(frozen=True)
class Envelope:
    """The wire format shared by every producer and consumer in the platform.

    Frozen because an envelope that a consumer can mutate is one that gets mutated
    *between* two handlers, after which nobody can say what was actually delivered.

    ``schema_version`` is what makes this evolvable: consumers dispatch on it, so a new
    field can be added (minor version) without a flag day, and only a change that consumers
    must react to costs a major.
    """

    key: str
    """Idempotency key. The same key twice means the same work twice, and handlers rely on
    that to make at-least-once delivery safe."""

    payload: dict[str, Any]
    """The message body. Never put a credential in here: envelopes are logged and replayed."""

    schema_version: int = 1
    """Version of ``payload``'s shape. Bump it additively; see docs/contracts.md."""

    emitted_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    """Producer-side timestamp, always timezone-aware UTC. A naive datetime crossing a
    process boundary is a bug that only appears when two services run in different zones."""

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dict. The inverse of :meth:`from_dict`."""
        return {
            "key": self.key,
            "payload": self.payload,
            "schema_version": self.schema_version,
            "emitted_at": self.emitted_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Envelope:
        """Parse an envelope, rejecting anything that is not one.

        Strict on purpose: a consumer that silently accepts a malformed message turns a
        producer bug into a data-corruption bug, and the two are then indistinguishable in
        the logs.
        """
        try:
            emitted_at = datetime.fromisoformat(raw["emitted_at"])
            return cls(
                key=raw["key"],
                payload=raw["payload"],
                schema_version=int(raw.get("schema_version", 1)),
                emitted_at=emitted_at,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"not a valid envelope: {exc}") from exc


def new_envelope(key: str, payload: dict[str, Any], schema_version: int = 1) -> Envelope:
    """Create an envelope with the current UTC timestamp.

    A factory rather than "just call the constructor" so the timestamp policy lives in one
    place: every producer would otherwise pick its own clock, and half of them would pick a
    naive local one.
    """
    return Envelope(key=key, payload=payload, schema_version=schema_version)
