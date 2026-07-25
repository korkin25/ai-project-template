"""Sample CLI (``app``). Replace with your real commands."""

from __future__ import annotations

import argparse

from app import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app", description="Sample app CLI")
    parser.add_argument("--version", action="version", version=f"app {__version__}")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("serve", help="run the HTTP service")
    args = parser.parse_args(argv)

    if args.command == "serve":
        from app.server import run

        run()
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
