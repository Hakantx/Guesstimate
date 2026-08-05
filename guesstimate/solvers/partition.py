"""The shared machinery behind minimax, expected-size, and entropy."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from guesstimate.core import Code

from .base import BaseSolver


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

    This is the naive implementation, and it is quadratic: every guess is scored
    against every survivor, every turn. That is deliberate. Phase 5 replaces the
    inner scoring with a lookup into a precomputed matrix, and the speedup is
    only worth reporting if there is an honest slow version to measure against.
    """

    def _choose(self) -> Code:
        return min(self.guess_pool, key=self._rank)

    def _rank(self, guess: Code) -> tuple[float, bool, int]:
        """The sort key deciding which guess wins. Lower is better throughout.

        Three parts, in order of authority:

        1. `_cost`, the strategy's own judgement of the split.
        2. Whether the guess is *not* still a candidate. The key sorts
           ascending and False sorts before True, so this puts guesses that
           could win outright ahead of equally informative ones that cannot.
           Encoding it the other way round -- True for "is a candidate" --
           silently prefers the guess that cannot win, costs a turn on every
           tie, and breaks no test that only checks the solver eventually wins.
        3. Position in the candidate space, so the remaining ties resolve in
           alphabet order rather than by dictionary iteration. Benchmarks have
           to reproduce exactly, which means no tie may be left to chance.
        """
        return (
            self._cost(self._partition(guess)),
            guess not in self._survivor_set,
            self._position[guess],
        )

    @abstractmethod
    def _cost(self, partition_sizes: Sequence[int]) -> float:
        """Judge a split by its group sizes. Lower is better.

        Implementations that naturally produce a "higher is better" quantity
        must negate it here -- see `EntropySolver`.
        """
