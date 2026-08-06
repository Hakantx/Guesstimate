"""One sitting at the terminal: both modes, and the play-again loop."""

from __future__ import annotations

import argparse
import random
from collections.abc import Callable

from rich.console import Console

from guesstimate.core import (
    Code,
    Feedback,
    Ruleset,
    all_candidates,
    format_code,
    parse_code,
    score,
)
from guesstimate.solvers import SOLVERS, InconsistentFeedbackError

from .display import board, collapse_line


class EndOfInputError(Exception):
    """The player pressed Ctrl-D, or a scripted session ran dry."""


class ScriptedInput:
    """Feeds prepared lines, for tests. Raises `EndOfInputError` when exhausted."""

    def __init__(self, lines: list[str]) -> None:
        self._lines = list(lines)

    def __call__(self, prompt: str) -> str:
        """Return the next scripted line."""
        if not self._lines:
            raise EndOfInputError
        return self._lines.pop(0)


def console_input(prompt: str) -> str:
    """Read one line from the terminal."""
    try:
        return input(prompt)
    except EOFError as error:
        raise EndOfInputError from error


class Session:
    """Drives the game, and is the only thing here that talks to a human.

    Input arrives through `ask` and output through `console`, both injected, so
    a whole game can be played in a test with scripted lines and a string
    buffer. Nothing below this class knows a terminal exists.
    """

    def __init__(
        self,
        console: Console,
        ask: Callable[[str], str],
        args: argparse.Namespace,
    ) -> None:
        self.console = console
        self.ask = ask
        self.args = args
        self.ruleset = Ruleset(
            length=args.length, alphabet=args.alphabet, allow_repeats=args.repeats
        )
        self.rng = random.Random(args.seed)

    # -- prompting ---------------------------------------------------------

    def _retry(self, message: str) -> None:
        self.console.print(f"[red]{message}[/red] Try again.")

    def ask_code(self, prompt: str) -> Code:
        """Read a code, re-prompting until it is one.

        The parse layer raises on anything malformed and this loop is the only
        thing that ever sees a raw string, which is the whole reason the
        original's crash-on-empty-line cannot happen here.
        """
        while True:
            try:
                return parse_code(self.ask(prompt), self.ruleset)
            except ValueError as error:
                self._retry(str(error))

    def ask_feedback(self, prompt: str) -> Feedback:
        """Read a `+B-C` answer, re-prompting until it is one."""
        while True:
            try:
                return Feedback.parse(self.ask(prompt))
            except ValueError as error:
                self._retry(str(error))

    def ask_yes(self, prompt: str) -> bool:
        """Read a yes/no, defaulting to no on anything unrecognised."""
        return self.ask(prompt).strip().lower().startswith("y")

    # -- modes -------------------------------------------------------------

    def secret(self) -> Code:
        """The secret for this game: fixed by `--secret`, or drawn from the seed."""
        if self.args.secret:
            return parse_code(self.args.secret, self.ruleset)
        return self.rng.choice(all_candidates(self.ruleset))

    def play_codebreaker(self) -> None:
        """Mode B: the player guesses, the computer scores."""
        secret = self.secret()
        played: list[tuple[Code, Feedback]] = []

        while True:
            guess = self.ask_code("guess> ")
            feedback = score(secret, guess)
            played.append((guess, feedback))
            self.console.print(board(played))
            if feedback.is_win(self.ruleset.length):
                self.console.print(
                    f"[green]You won in {len(played)}.[/green] "
                    f"The code was {format_code(secret)}."
                )
                return

    def play_solver(self) -> None:
        """Mode A: the computer guesses, the player scores. The original game."""
        solver = SOLVERS[self.args.solver](self.ruleset, rng=self.rng)
        secret = self.secret() if self.args.auto_answer else None
        played: list[tuple[Code, Feedback]] = []
        counts = [len(solver.candidates)]
        total = counts[0]

        self.console.print(
            f"Think of a code. I have {total:,} to choose from.\n"
            f"Answer each guess as [bold]+bulls-cows[/bold], for example +2-1."
        )

        while True:
            if self.args.stop_after and len(played) >= self.args.stop_after:
                self.console.print("[dim]Stopping here.[/dim]")
                return

            guess = solver.guess()
            self.console.print(f"\nMy guess: [bold]{format_code(guess)}[/bold]")

            if secret is not None:
                feedback = score(secret, guess)
                self.console.print(f"[dim]auto-answer: {feedback}[/dim]")
            else:
                feedback = self.ask_feedback("your answer> ")

            if feedback.is_win(self.ruleset.length):
                played.append((guess, feedback))
                self.console.print(board(played))
                self.console.print(
                    f"[green]Got it in {len(played)}.[/green] "
                    f"The code was {format_code(guess)}."
                )
                return

            try:
                solver.update(guess, feedback)
            except InconsistentFeedbackError as error:
                # A human scoring by hand gets this wrong regularly. The turn is
                # dropped and the solver is left exactly as it was, so the game
                # continues from the last answer that made sense.
                self.console.print(
                    f"[red]That contradicts an earlier answer.[/red] {error}"
                )
                self.console.print("[dim]Ignoring it. Answer again.[/dim]")
                continue

            played.append((guess, feedback))
            counts.append(len(solver.candidates))
            self.console.print(board(played))
            self.console.print(collapse_line(counts, total))

    # -- the loop ----------------------------------------------------------

    def play(self) -> None:
        """Play games until the player stops or the input runs out."""
        try:
            # Asked once. A player who chose a mode wants to play that mode
            # again, and re-prompting between games reads as a bug.
            mode = self.args.mode or self.ask(
                "[a] I guess, you score  [b] you guess, I score > "
            )
            while True:
                if mode.strip().lower().startswith("a"):
                    self.play_solver()
                else:
                    self.play_codebreaker()

                if not self.ask_yes("\nAnother? [y/N] > "):
                    self.console.print("Thanks for playing.")
                    return
        except EndOfInputError:
            self.console.print("\nBye.")
