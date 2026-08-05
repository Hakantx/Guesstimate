"""The interface every strategy implements.

Deliberately narrow. It describes what a solver *does* -- offer a guess, absorb
an answer, expose what is still possible -- and says nothing about how one is
built. That is what lets Phase 5 hand the matrix-backed solvers an extra
constructor argument without this file, the API, or the UI changing at all.
"""

from typing import Protocol

from guesstimate.core import Code, Feedback


class InconsistentFeedbackError(ValueError):
    """An answer that contradicts an earlier one.

    Raised when narrowing would leave no candidate at all. That is never the
    engine's fault: it means a human scoring the game made a mistake, or two
    answers disagree about the same secret. Callers are expected to catch this
    and offer a correction -- the CLI by undoing the last turn, the API by
    rejecting the request -- so that `Solver.candidates` is never empty.
    """


class Solver(Protocol):
    """A codebreaking strategy.

    Implementations hold their own candidate set and narrow it as answers
    arrive. A solver plays one game; to play another, build another.
    """

    @property
    def candidates(self) -> tuple[Code, ...]:
        """Every code still consistent with all feedback so far.

        Never empty: an answer that would empty it raises
        `InconsistentFeedbackError` instead. Ordered as `all_candidates`
        orders the full space, which is what the Phase 7 grid animates.

        A tuple, not a `Sequence`, and deliberately so. `Sequence` is read-only
        only to the type checker -- an implementation returning its own list
        would hand callers a live handle on solver state, and the Phase 6 API
        would pass that straight out to route handlers. Requiring a tuple makes
        the guarantee real at runtime for every implementation, and costs
        nothing if the snapshot is built when the candidate set changes rather
        than when it is read.
        """
        ...

    def guess(self) -> Code:
        """The next code to try.

        Does not mutate anything, so asking twice without an intervening
        `update` is allowed. Deterministic strategies answer identically both
        times; `RandomSolver` re-samples.
        """
        ...

    def update(self, guess: Code, feedback: Feedback) -> None:
        """Narrow the candidate set by one answer.

        The guess need not be one this solver proposed -- in race mode a human
        plays their own codes against the same solver state.

        Raises:
            InconsistentFeedbackError: If no candidate survives the answer.
        """
        ...
