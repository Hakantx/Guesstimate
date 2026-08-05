"""Turning game records into numbers that mean something."""

from __future__ import annotations

import math
import statistics
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from guesstimate.core import Ruleset, feedback_space

from .harness import RunResult
from .records import GameRecord


@dataclass(frozen=True)
class PairedDifference:
    """How much better one solver is than another, secret by secret.

    Comparing two solvers by their means throws away the fact that they played
    the same secrets. Some secrets are simply harder than others -- that
    difficulty appears in both means as noise, and on this game it is large:
    guess counts on the classic ruleset spread across roughly 3 to 6, while the
    gap between good strategies is under a tenth of a guess.

    Differencing per secret cancels that entirely. If a secret costs everyone
    an extra turn, the difference for that secret is unaffected. What is left
    is the effect being measured, and its spread is far smaller than either
    solver's own spread, so a gap of 0.08 becomes something worth reporting
    rather than something lost inside a standard deviation of 0.9.

    Positive `mean` means the contender used fewer guesses than the baseline.
    """

    mean: float
    stdev: float
    stderr: float
    wins: int
    losses: int
    ties: int
    n: int

    @property
    def confidence_interval(self) -> tuple[float, float]:
        """Normal-approximation 95% interval on the mean difference.

        An interval that excludes zero is the bar for claiming a real
        difference. The approximation is fine at the sample sizes here and
        avoids a scipy dependency for a t-distribution correction that changes
        the third decimal.
        """
        margin = 1.96 * self.stderr
        return (self.mean - margin, self.mean + margin)

    @property
    def is_significant(self) -> bool:
        """Whether the interval clears zero in either direction."""
        low, high = self.confidence_interval
        return low > 0 or high < 0


def per_secret_guesses(records: Sequence[GameRecord]) -> list[float]:
    """One number per secret, averaging any repeats.

    For a deterministic solver this is just its guess count. For the random
    baseline, played several times per secret, it is the mean over those plays
    -- an estimate of expected performance on that secret rather than one draw
    from it. That distinction is what makes the baseline pairable at all: a
    single random game carries the solver's own coin flips, which correlate
    with nothing, so differencing against it cancels no shared difficulty.
    """
    grouped: dict[int, list[int]] = {}
    for record in records:
        grouped.setdefault(record.secret_index, []).append(record.guesses)
    return [statistics.mean(grouped[index]) for index in sorted(grouped)]


def paired_difference(
    baseline: Sequence[float], contender: Sequence[float]
) -> PairedDifference:
    """Difference the two runs secret by secret.

    Both sequences must be the same length and in sample order, so index `i` is
    the same secret on both sides. That is the entire basis of the method.
    """
    if len(baseline) != len(contender):
        raise ValueError(
            "paired comparison needs the same secrets on both sides, got "
            f"{len(baseline)} and {len(contender)}"
        )
    if not baseline:
        raise ValueError("paired comparison needs at least one secret")

    diffs = [float(b) - float(c) for b, c in zip(baseline, contender, strict=True)]
    stdev = statistics.stdev(diffs) if len(diffs) > 1 else 0.0
    return PairedDifference(
        mean=statistics.mean(diffs),
        stdev=stdev,
        stderr=stdev / math.sqrt(len(diffs)),
        wins=sum(1 for d in diffs if d > 0),
        losses=sum(1 for d in diffs if d < 0),
        ties=sum(1 for d in diffs if d == 0),
        n=len(diffs),
    )


@dataclass(frozen=True)
class Summary:
    """The shape of one solver's results.

    Timings are split deliberately. `cold_open_seconds` is the first guess on
    an empty opening cache -- the full search over the whole space, paid once
    per configuration. `warm_*` covers every game after that. On the classic
    ruleset those differ by a factor of about 25, so averaging them together
    would produce a per-game figure that describes no game that was played.
    """

    config: str
    n: int
    games: int
    repeats: int
    mean: float
    median: float
    worst: int
    stdev: float
    distribution: dict[int, int]
    collapse: tuple[float, ...]
    cold_open_seconds: float
    warm_mean_seconds: float
    warm_median_seconds: float
    warm_stdev_seconds: float
    turn_mean_seconds: float

    @property
    def guess_counts(self) -> list[int]:
        """Rebuilt from the histogram, for eyeballing only."""
        return [
            count for count, times in self.distribution.items() for _ in range(times)
        ]


def summarise(result: RunResult) -> Summary:
    """Reduce one configuration's games to its published row."""
    ordered = sorted(result.records, key=lambda r: (r.secret_index, r.repeat))
    counts = [r.guesses for r in ordered]
    times = [r.seconds for r in ordered]
    turn_times = [t for r in ordered for t in r.turn_seconds]

    per_secret = per_secret_guesses(ordered)
    return Summary(
        config=result.config.name,
        n=len(per_secret),
        games=len(ordered),
        repeats=len(ordered) // max(1, len(per_secret)),
        mean=statistics.mean(counts),
        median=statistics.median(counts),
        worst=max(counts),
        stdev=statistics.stdev(counts) if len(counts) > 1 else 0.0,
        distribution=dict(sorted(Counter(counts).items())),
        collapse=_collapse_curve(ordered),
        cold_open_seconds=result.cold_open_seconds,
        warm_mean_seconds=statistics.mean(times),
        warm_median_seconds=statistics.median(times),
        warm_stdev_seconds=statistics.stdev(times) if len(times) > 1 else 0.0,
        turn_mean_seconds=statistics.mean(turn_times) if turn_times else 0.0,
    )


def _collapse_curve(records: Sequence[GameRecord]) -> tuple[float, ...]:
    """Mean candidates left after guess 1, 2, 3, and so on.

    Games end at different lengths. A game that finished in three guesses has
    one candidate left at every later turn -- it is solved, not missing -- so
    short games are padded with 1 rather than dropped, which would bias the
    tail towards whichever games happened to run long.
    """
    longest = max(3, max(len(r.survivors) for r in records))
    curve = []
    for turn in range(longest):
        curve.append(
            statistics.mean(
                r.survivors[turn] if turn < len(r.survivors) else 1 for r in records
            )
        )
    return tuple(curve)


def information_floor(ruleset: Ruleset) -> float:
    """The fewest guesses any strategy could average, in principle.

    Each guess returns one of a fixed number of outcomes, so a game of `g`
    guesses can distinguish at most `outcomes ** g` secrets. To separate every
    secret in the space needs `outcomes ** g >= space`, giving
    `g >= log2(space) / log2(outcomes)`. For the classic game that is
    log2(3024)/log2(14), about 3.04.

    It uses the *reachable* outcomes, not every pair with bulls + cows <=
    length. Rulesets with small alphabets reach far fewer than the triangle
    suggests, and assuming the triangle would understate the floor and make
    solvers look further from optimal than they are.

    No real strategy reaches this bound -- it assumes every guess splits the
    space perfectly evenly, which no single code does. The gap between it and
    the best solver is the interesting quantity, not the bound itself.
    """
    if ruleset.space_size <= 1:
        return 1.0
    outcomes = len(feedback_space(ruleset))
    if outcomes <= 1:
        return float("inf")
    return max(1.0, math.log2(ruleset.space_size) / math.log2(outcomes))
