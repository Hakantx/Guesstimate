"""Turning a loss into a word.

The thresholds are measured, not chosen. Round numbers would encode a guess
about what counts as a bad move, and the whole point of the metric is that
intuition about that is unreliable -- eliminating a lot of candidates feels
good and can be the worse guess.
"""

from __future__ import annotations

from enum import StrEnum


class Grade(StrEnum):
    """How a move compares to the best that was available."""

    BEST = "best"
    GOOD = "good"
    INACCURACY = "inaccuracy"
    MISTAKE = "mistake"
    BLUNDER = "blunder"


#: Loss thresholds as a *fraction of the candidates standing*, so a move is
#: judged relative to its position rather than in absolute candidates. Giving up
#: 40 expected candidates out of 3,024 is a rounding error; giving up 40 out of
#: 60 is the game.
#:
#: Cut at percentiles of the measured per-move loss distribution -- 10,679 moves
#: from 600 seeded secrets played by all four solvers on the classic ruleset:
#:
#:     p50  0.0000     p90  0.0050     p99  0.1250
#:     p75  0.0000     p95  0.0223     max  0.6250
#:
#: Three quarters of all moves give up nothing at all, which is why `BEST` is
#: exact zero rather than a small tolerance: a band that swallowed the median
#: would tell most players nothing.
BANDS: tuple[tuple[float, Grade], ...] = (
    (0.0, Grade.BEST),  # gave up nothing
    (0.0050, Grade.GOOD),  # within the 90th percentile
    (0.0223, Grade.INACCURACY),  # within the 95th
    (0.1250, Grade.MISTAKE),  # within the 99th
)  # beyond that, a blunder


#: The smallest loss share that costs a move its perfect grade. Reused as the
#: bar for "is this difference worth mentioning at all", so the interface does
#: not need a second opinion about what counts as significant.
NOTICEABLE = BANDS[1][0]


def grade_for(loss: float, survivors: int) -> Grade:
    """Grade a move by how much it gave up, relative to the position."""
    if survivors <= 1:
        return Grade.BEST  # nothing to choose between
    share = max(0.0, loss) / survivors

    grade = Grade.BLUNDER
    for threshold, band in BANDS:
        if share <= threshold:
            return band
        grade = Grade.BLUNDER
    return grade
