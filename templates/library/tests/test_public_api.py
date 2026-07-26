"""Tier-(a) tests for @@PROJECT@@ — the public API is the product, so it is what is tested.

Two of these tests are unusual and deliberate:

* :func:`test_every_public_symbol_is_documented` fails the build when a symbol is exported
  but missing from ``docs/contracts.md``. The registry is only useful if it cannot drift,
  and a doc that drifts is worse than no doc — a consumer trusts it.
* :func:`test_no_accidental_exports` fails when a module-level name is public but not in
  ``__all__``. Without it, a helper becomes part of the contract the moment someone imports
  it, and the first anyone hears of it is a bug report about its removal.

There is no image and no chart here, so `/functional.yml` is not included in this repo's CI
and this suite is the whole of tier (a). It therefore runs with PYTEST_ALLOW_NO_TESTS=false.
"""

from __future__ import annotations

import inspect
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

import @@PKG@@ as lib
from @@PKG@@ import Envelope, new_envelope

CONTRACTS = Path(__file__).resolve().parents[1] / "docs" / "contracts.md"


def test_all_is_sorted_and_importable() -> None:
    """Everything promised in ``__all__`` actually exists (a typo there is a broken import
    for every consumer using ``from @@PKG@@ import *``)."""
    assert lib.__all__ == sorted(lib.__all__), "__all__ is kept sorted so diffs stay readable"
    for name in lib.__all__:
        assert hasattr(lib, name), f"{name} is exported but not defined"


def test_every_public_symbol_is_documented() -> None:
    """`docs/contracts.md` is the registry other repos read — it must list every export."""
    documented = set(re.findall(r"`([A-Za-z_][A-Za-z0-9_.]*)`", CONTRACTS.read_text("utf-8")))
    missing = [name for name in lib.__all__ if name not in documented]
    assert not missing, (
        f"exported but undocumented: {missing}. Add them to docs/contracts.md in this same "
        f"change — a consumer may only rely on what that file promises."
    )


def test_no_accidental_exports() -> None:
    """A public name defined in this package must be an intentional part of the contract."""
    leaked = [
        name
        for name, obj in vars(lib).items()
        if not name.startswith("_")
        and getattr(obj, "__module__", None) == lib.__name__
        and name not in lib.__all__
    ]
    assert not leaked, (
        f"public but not in __all__: {leaked}. Either prefix them with '_' (internal) or add "
        f"them to __all__ and docs/contracts.md (public, and therefore permanent)."
    )


def test_public_symbols_are_typed_and_documented() -> None:
    """Every export carries a docstring — the API is what consumers read instead of the source."""
    for name in lib.__all__:
        obj = getattr(lib, name)
        if inspect.isclass(obj) or inspect.isfunction(obj):
            assert obj.__doc__, f"{name} has no docstring"


def test_envelope_round_trips() -> None:
    envelope = new_envelope("k1", {"a": 1})

    restored = Envelope.from_dict(envelope.to_dict())

    assert restored == envelope


def test_envelope_timestamp_is_timezone_aware() -> None:
    """A naive datetime crossing a process boundary breaks only in production."""
    assert new_envelope("k1", {}).emitted_at.tzinfo is not None


def test_envelope_is_immutable() -> None:
    envelope = new_envelope("k1", {})

    with pytest.raises(Exception):  # noqa: B017 - dataclasses raise FrozenInstanceError
        envelope.key = "k2"  # type: ignore[misc]


def test_from_dict_rejects_a_malformed_message() -> None:
    """Loud failure beats a half-parsed envelope flowing on to a handler."""
    with pytest.raises(ValueError):
        Envelope.from_dict({"payload": {}})


def test_schema_version_defaults_to_one() -> None:
    """The default is part of the contract: an old producer omits the field entirely."""
    raw = {"key": "k", "payload": {}, "emitted_at": datetime.now(UTC).isoformat()}

    assert Envelope.from_dict(raw).schema_version == 1
