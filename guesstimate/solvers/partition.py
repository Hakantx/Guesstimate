"""The shared machinery behind minimax, expected-size, and entropy."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from guesstimate.core import Code, Ruleset

from .base import BaseSolver
from .partitioner import CodeIndex

# Opening moves, keyed by what actually determines them.
#
# The first guess of a game is computed from the full candidate set, which is
# the same for every game with the same ruleset, using a ranking key that is a
# total order with no randomness in it. So the opening is provably identical
# every time, and computing it once per (strategy, ruleset, restriction) rather
# than once per game costs nothing in accuracy.
#
# It buys a great deal in time. Turn one scores every guess against every
# candidate -- 3024 x 3024 for the classic game -- while turn two works on the
# couple of hundred that survived. Measured on the reference machine, one naive
# minimax game on the classic ruleset:
#
#     turn 1   pool 3024   49.750s   99.5%
#     turn 2   pool  220    0.253s    0.5%
#     turn 3   pool   60    0.018s    0.0%
#     turn 4   pool   12    0.001s    0.0%
#
# Expected-size and entropy are within a second of that. The opening is not
# most of the cost, it is essentially all of it, so without this a benchmark
# over 3024 secrets would spend two days recomputing one answer it already had.
# With it, measured over 30 warm games, a game costs 2.13s on average (sd 1.62)
# and a 3024-secret sweep drops from ~43 hours to ~108 minutes.
#
# Three things this is not. It is not I/O, so it does not touch CLAUDE.md rule
# 1: nothing is read or written, and the cache is pure memoisation -- same
# inputs, same output, no observable behaviour change. It is not the Phase 5
# optimisation, which replaces the per-turn scoring itself with matrix lookups
# and is measured per turn, on a cold cache. And it deliberately does not apply
# to RandomSolver, which is not a PartitionSolver: its opening is supposed to
# vary with its seed, and caching it would silently make every game start the
# same way.
#
# Process-local by design. Phase 3's parallelism is process-level, so each
# worker builds its own cache and no locking is involved.
_OPENING_CACHE: dict[tuple[type["PartitionSolver"], Ruleset, bool], Code] = {}


def clear_opening_cache() -> None:
    """Forget every cached opening.

    Benchmarks call this to time a cold first turn, which is the honest naive
    cost and the number Phase 5's speedup is measured against.
    """
    _OPENING_CACHE.clear()


class PartitionSolver(BaseSolver, ABC):
    """Scores every guess by the shape of the split it would produce.

    All three scoring strategies do the same work. For each guess in the pool,
    group the surviving candidates by the feedback that guess would draw, then
    judge the resulting group sizes. A guess is good when it carves the
    survivors into small pieces, because whichever piece the real secret is in
    is all that survives the turn.

    They differ only in what "small pieces" means -- the largest piece, the
    average piece, or the information the split reveals -- so that judgement is
    the single abstract method here.

    The search itself is naive and quadratic: every guess is scored against
    every survivor, every turn. That is deliberate. Phase 5 replaces the inner
    scoring with a lookup into a precomputed matrix, and the speedup is only
    worth reporting if there is an honest slow version to measure against.
    """

    def _choose(self) -> Code:
        if self._answers:
            return self._search()

        key = (type(self), self.ruleset, self.restrict_to_candidates)
        opening = _OPENING_CACHE.get(key)
        if opening is None:
            opening = self._search()
            _OPENING_CACHE[key] = opening
        return opening

    def _search(self) -> Code:
        return self._space[min(self._pool, key=self._rank)]

    def _rank(self, guess: CodeIndex) -> tuple[float, bool, int]:
        """The sort key deciding which guess wins. Lower is better throughout.

        Three parts, in order of authority:

        1. `_cost`, the strategy's own judgement of the split.
        2. Whether the guess is *not* still a candidate. The key sorts
           ascending and False sorts before True, so this puts guesses that
           could win outright ahead of equally informative ones that cannot.
           Encoding it the other way round -- True for "is a candidate" --
           silently prefers the guess that cannot win, costs a turn on every
           tie, and breaks no test that only checks the solver eventually wins.
        3. The index itself, so the remaining ties resolve in alphabet order
           rather than by dictionary iteration. Benchmarks have to reproduce
           exactly, which means no tie may be left to chance. Indices are
           positions in `all_candidates`, so comparing them *is* comparing
           alphabet order -- no side table, and nothing to keep in sync.
        """
        return (
            self._cost(self._partition(guess)),
            guess not in self._survivor_set,
            guess,
        )

    @abstractmethod
    def _cost(self, partition_sizes: Sequence[int]) -> float:
        """Judge a split by its group sizes. Lower is better.

        Implementations that naturally produce a "higher is better" quantity
        must negate it here -- see `EntropySolver`.
        """
