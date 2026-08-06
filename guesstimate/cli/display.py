"""Rendering. Everything that decides how the terminal looks lives here."""

from __future__ import annotations

import math
from collections.abc import Sequence

from rich.table import Table
from rich.text import Text

from guesstimate.core import Code, Feedback

BLOCKS = "▁▂▃▄▅▆▇█"


def sparkline(values: Sequence[int]) -> str:
    """A one-line picture of the candidate set collapsing.

    Log-scaled, and that is the whole point. The classic game goes 3024 -> 240
    -> 20 -> 1, so on a linear scale the first guess uses the entire height and
    every later step sits on the floor, which draws a cliff and then nothing.
    Taking logs first turns "divided by roughly ten, four times" into four
    even steps, which is what the collapse actually is.
    """
    if not values:
        return ""

    scaled = [math.log10(max(1, value)) for value in values]
    low, high = min(scaled), max(scaled)
    if high - low < 1e-9:
        return BLOCKS[len(BLOCKS) // 2] * len(values)

    marks = []
    for value in scaled:
        position = (value - low) / (high - low)
        marks.append(BLOCKS[min(len(BLOCKS) - 1, int(position * len(BLOCKS)))])
    return "".join(marks)


def board(guesses: Sequence[tuple[Code, Feedback]]) -> Table:
    """The turns played so far."""
    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("#", justify="right", width=3)
    table.add_column("guess")
    table.add_column("score")
    table.add_column("bulls", justify="left")
    for turn, (guess, feedback) in enumerate(guesses, start=1):
        # Shape as well as colour: feedback has to survive a screenshot, a
        # colourblind reader, and a terminal that ignores ANSI.
        pips = "●" * feedback.bulls + "○" * feedback.cows
        table.add_row(str(turn), "".join(guess), str(feedback), pips)
    return table


def collapse_line(counts: Sequence[int], total: int) -> Text:
    """Surviving candidates, with the sparkline of how they got there."""
    text = Text()
    text.append(f"{counts[-1]:>6,} ", style="bold")
    text.append(f"of {total:,} left  ", style="dim")
    text.append(sparkline(counts))
    return text
