"""What a guess was worth at the position it was played from."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from guesstimate.solvers.partitioner import CandidateSet, CodeIndex, Partitioner


def expected_remaining(sizes: Sequence[int], total: int, wins: bool) -> float:
    """Candidates still standing after this guess, in expectation.

    Each block is reached with probability `|B| / total` and leaves `|B|`
    candidates, so the expectation is the sum of `|B|^2 / total`.

    With one correction, and it is a correction rather than a preference. The
    question this answers is "how many candidates am I still facing once the
    answer arrives", and after the winning answer that number is zero -- the
    game is over. Counting the winning candidate as one still remaining is
    wrong on the metric's own terms, independently of what any solver does.

    The win block holds exactly one code when the guess is itself still
    possible, and none otherwise: an all-bulls answer means every position
    matches, which only the guess itself does. So the correction is a single
    `1 / total`, and it is what makes a guess that could win outright score
    better than an otherwise identical one that cannot.
    """
    if total <= 0:
        return 0.0
    weighted = sum(size * size for size in sizes) / total
    return weighted - (1.0 / total if wins else 0.0)


def bits_gained(sizes: Sequence[int], total: int) -> float:
    """Information the answer reveals, in bits.

    Reported beside `expected_remaining` rather than instead of it. The two
    usually agree about which guess is better and disagree about by how much,
    and a player learns more from "this left 40 candidates where 12 was
    available" than from a number of bits.
    """
    if total <= 0:
        return 0.0
    entropy = 0.0
    for size in sizes:
        if size:
            share = size / total
            entropy -= share * math.log2(share)
    return entropy


@dataclass(frozen=True)
class Best:
    """The best available at a position, from each pool."""

    among_candidates: float
    among_all: float
    best_candidate: CodeIndex | None
    best_any: CodeIndex | None


def best_at(
    partitioner: Partitioner,
    survivors: CandidateSet,
    universe: CandidateSet,
) -> Best:
    """The lowest expected remaining any guess could have achieved here.

    Two pools, and the grading one is deliberately the narrower.

    Grading against every code in the space would measure a human against
    specialist probes -- guesses that cannot win but split the survivors
    slightly better. The full-sweep benchmark puts that advantage at about a
    tenth of a guess for entropy and nothing at all for the other strategies,
    so grading against it would use a small effect to mark down sensible play.

    The wider pool is computed anyway and shown alongside, because the gap
    between the two is exactly the lesson about when a probe is worth a turn.
    """
    alive = set(int(index) for index in survivors)
    total = len(alive)

    among_candidates = math.inf
    among_all = math.inf
    best_candidate: CodeIndex | None = None
    best_any: CodeIndex | None = None

    for guess in universe:
        index = CodeIndex(int(guess))
        sizes = partitioner.sizes(index, survivors)
        value = expected_remaining(sizes, total, index in alive)
        if value < among_all:
            among_all, best_any = value, index
        if index in alive and value < among_candidates:
            among_candidates, best_candidate = value, index

    return Best(
        among_candidates=among_candidates,
        among_all=among_all,
        best_candidate=best_candidate,
        best_any=best_any,
    )
