"""Group-(a) tests for the sample CLI (``app``). Replace with your real tests.

These exist for a reason beyond the sample: `cli.py` was the one module in this repository
with no test at all, which is what made a coverage threshold impossible to set honestly —
any number that passed would have been a number chosen to accommodate the gap.
"""

from __future__ import annotations

import pytest

from app import __version__
from app.cli import main


def test_version_flag_prints_version_and_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    """``--version`` is argparse's own action, so it raises SystemExit rather than returning."""
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_no_command_prints_help_and_succeeds(capsys: pytest.CaptureFixture[str]) -> None:
    """A bare invocation is not an error — it is a discovery step, so it must exit 0."""
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "usage:" in out
    assert "serve" in out


def test_unknown_command_exits_nonzero(capsys: pytest.CaptureFixture[str]) -> None:
    """argparse rejects an unknown subcommand with exit 2; a CLI that accepted it silently
    would be indistinguishable from one that ran it."""
    with pytest.raises(SystemExit) as exc:
        main(["nonsense"])
    assert exc.value.code != 0


def test_serve_delegates_to_the_server(monkeypatch: pytest.MonkeyPatch) -> None:
    """`serve` must call `app.server.run` and return 0.

    The import inside `main` is deliberate — it keeps the server module off the import path
    of every other command — so the patch targets `app.server.run`, where the name is looked
    up, rather than a name bound into `cli`.
    """
    called = False

    def fake_run() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr("app.server.run", fake_run)
    assert main(["serve"]) == 0
    assert called, "serve returned 0 without ever starting the server"
