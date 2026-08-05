"""The baseline: guess anything that could still be the secret."""

from guesstimate.core import Code

from .base import BaseSolver


class RandomSolver(BaseSolver):
    """Picks uniformly at random from the surviving candidates.

    This is what the 2021 original did, and it is here to be beaten. It is not a
    bad strategy -- never guessing something already ruled out is most of what
    makes a solver work -- it just never asks which of the survivors would teach
    it the most.

    `restrict_to_candidates` has no effect on this solver. Guessing at random
    from the full space would mean usually guessing a code already known to be
    impossible, which cannot win the turn and turns the baseline into noise. The
    flag is accepted anyway so that every strategy is built the same way.
    """

    def _choose(self) -> Code:
        return self._rng.choice(self._candidates)
