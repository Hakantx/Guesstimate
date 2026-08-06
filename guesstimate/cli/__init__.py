"""The terminal version.

Does I/O, obviously, and is a thin shell over `core` and `solvers` -- no game
logic lives here. It is also the first thing in the repo to exercise CLAUDE.md
rule 10: this is the local, in-process path, with no server anywhere in it.
"""

from __future__ import annotations

import argparse
import sys

from rich.console import Console

from guesstimate.core import Ruleset
from guesstimate.solvers import SOLVERS

from .session import Session, console_input

__all__ = ["Session", "build_parser", "main"]


def build_parser() -> argparse.ArgumentParser:
    """Flags for the game."""
    parser = argparse.ArgumentParser(
        prog="guesstimate", description="Bulls and Cows, in the terminal."
    )
    parser.add_argument("--solver", choices=sorted(SOLVERS), default="minimax")
    parser.add_argument("--length", type=int, default=4)
    parser.add_argument("--alphabet", default="123456789")
    parser.add_argument("--repeats", action="store_true")
    parser.add_argument(
        "--seed", type=int, default=None, help="reproducible secrets and solver draws"
    )
    parser.add_argument(
        "--mode",
        choices=["a", "b"],
        default=None,
        help="skip the menu: a = I guess, b = you guess",
    )
    parser.add_argument(
        "--secret", default=None, help="fix the code, for demos and tests"
    )
    parser.add_argument(
        "--auto-answer",
        action="store_true",
        help="score the solver's guesses automatically, for demos",
    )
    parser.add_argument(
        "--stop-after", type=int, default=0, help="end a solver game after N turns"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a shell exit code and never raises at the user."""
    args = build_parser().parse_args(argv)
    console = Console()

    try:
        Ruleset(length=args.length, alphabet=args.alphabet, allow_repeats=args.repeats)
    except ValueError as error:
        console.print(f"[red]Impossible ruleset:[/red] {error}")
        return 2

    try:
        Session(console=console, ask=console_input, args=args).play()
    except KeyboardInterrupt:
        console.print("\nBye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
