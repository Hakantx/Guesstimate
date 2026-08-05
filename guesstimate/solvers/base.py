"""Candidate bookkeeping, shared by every strategy."""

import random
from abc import ABC, abstractmethod
from collections import Counter
from collections.abc import Sequence

from guesstimate.core import (
    Code,
    Feedback,
    Ruleset,
    all_candidates,
    filter_candidates,
    score,
)

from .protocol import InconsistentFeedbackError


class BaseSolver(ABC):
    """Everything a strategy needs except the strategy.

    Holds the surviving candidates, narrows them on each answer, and leaves
    exactly one thing to subclasses: `_choose`. A fifth strategy is one file
    and one method, with no change here, to any other solver, or to the API.

    All four solvers share this constructor signature so callers can build any
    of them the same way -- the CLI's `--solver` flag and the registry in
    `__init__` both depend on that.

    Args:
        ruleset: The game being played.
        restrict_to_candidates: When True, only guess codes that could still be
            the secret. When False, guess anything in the full space, including
            codes already ruled out. Unrestricted is stronger: a guess that
            cannot possibly win can still split the survivors better than any
            that can, and the extra turn it costs is often repaid. It is also
            far slower, since the pool stays at full size every turn.
        rng: Source of randomness, injected so benchmarks reproduce. Only
            `RandomSolver` uses it; the other three break ties deterministically
            and ignore it, but they accept it to keep the signature uniform.
    """

    def __init__(
        self,
        ruleset: Ruleset,
        *,
        restrict_to_candidates: bool = True,
        rng: random.Random | None = None,
    ) -> None:
        self.ruleset = ruleset
        self.restrict_to_candidates = restrict_to_candidates
        self._rng = random.Random() if rng is None else rng
        self._space = all_candidates(ruleset)
        # Position in the full space, used to break ties. This is what "lowest
        # first" means: alphabet order, not the tuples' own comparison order,
        # which would sort by character code and diverge the moment a ruleset
        # uses an alphabet that is not already in ascending order.
        self._position = {code: index for index, code in enumerate(self._space)}
        self._candidates = list(self._space)
        self._survivor_set = set(self._candidates)

    @property
    def candidates(self) -> Sequence[Code]:
        """Codes still consistent with every answer so far.

        Never empty -- an answer that would empty it raises instead. Typed as a
        read-only sequence; callers must not mutate what they get back.
        """
        return self._candidates

    @property
    def guess_pool(self) -> Sequence[Code]:
        """The codes this solver will consider guessing this turn."""
        return self._candidates if self.restrict_to_candidates else self._space

    def guess(self) -> Code:
        """The next code to try. Does not change the solver's state."""
        return self._choose()

    def update(self, guess: Code, feedback: Feedback) -> None:
        """Narrow the candidate set by one answer.

        Raises:
            InconsistentFeedbackError: If no candidate survives, which means an
                earlier answer contradicts this one.
        """
        survivors = filter_candidates(self._candidates, guess, feedback)
        if not survivors:
            raise InconsistentFeedbackError(
                f"no code can answer {feedback} to {''.join(guess)} and still "
                f"match every earlier answer; one of them must be wrong"
            )
        self._candidates = survivors
        self._survivor_set = set(survivors)

    def _partition(self, guess: Code) -> list[int]:
        """Sizes of the groups this guess would split the survivors into.

        Every candidate produces exactly one feedback for a given guess, so the
        groups partition the surviving set and their sizes sum to it. How good a
        guess is depends only on the shape of that split, never on which
        feedback produced which group -- which is why the three scoring solvers
        can share this and differ by one line.
        """
        counts: Counter[Feedback] = Counter(
            score(candidate, guess) for candidate in self._candidates
        )
        return list(counts.values())

    @abstractmethod
    def _choose(self) -> Code:
        """Pick a guess. The one thing a strategy has to supply."""
