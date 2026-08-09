"""Candidate bookkeeping, shared by every strategy."""

import random
from abc import ABC, abstractmethod
from collections.abc import Sequence

from guesstimate.core import Code, Feedback, Ruleset, all_candidates

from .partitioner import CandidateSet, CodeIndex, Partitioner, PurePartitioner
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
            codes already ruled out. The argument for unrestricted is that a
            guess which cannot win may still split the survivors better than
            any that can. That is expectation, not measurement -- Phase 3
            benchmarks both and settles it. What is certain is that
            unrestricted is far slower, since the pool never shrinks.
        rng: Source of randomness, injected so benchmarks reproduce. Only
            `RandomSolver` uses it; the other three break ties deterministically
            and ignore it, but they accept it to keep the signature uniform.
        partitioner: How the solver finds out what a guess does to the
            candidate set. Defaults to scoring on demand. Pass a matrix-backed
            one from `guesstimate.data` to make the same strategy fast --
            solvers never build or load one themselves, which is what keeps
            this layer free of numpy and of I/O.
    """

    #: Whether two runs on the same secret can differ. The three scoring
    #: strategies are fully determined by the ruleset, so repeating one is
    #: wasted work; `RandomSolver` is not, and its score for a secret is one
    #: draw from a distribution rather than a property of the secret.
    stochastic: bool = False

    def __init__(
        self,
        ruleset: Ruleset,
        *,
        restrict_to_candidates: bool = True,
        rng: random.Random | None = None,
        partitioner: Partitioner | None = None,
    ) -> None:
        self.ruleset = ruleset
        self.restrict_to_candidates = restrict_to_candidates
        self._rng = random.Random() if rng is None else rng
        self._partitioner = (
            PurePartitioner(ruleset) if partitioner is None else partitioner
        )
        self._space = tuple(all_candidates(ruleset))
        # Everything below the public surface is an index into `_space`. That
        # ordering is already what "lowest first" means for the tie-break --
        # alphabet order, not the tuples' own comparison order, which would sort
        # by character code and diverge the moment an alphabet is not ascending
        # -- so an index is its own tie-break position and needs no side table.
        self._universe: CandidateSet = self._partitioner.universe()
        self._index_of = {code: CodeIndex(i) for i, code in enumerate(self._space)}
        self._indices: CandidateSet = self._universe
        self._survivor_set = set(self._indices)
        # Both public views are built on demand and cached until the next
        # answer. A caller that only wants the grid never pays to materialise
        # symbols, and a caller that only wants symbols never pays twice.
        self._index_snapshot: tuple[CodeIndex, ...] | None = None
        self._code_snapshot: tuple[Code, ...] | None = None
        # How many answers this solver has absorbed. Zero means it is still on
        # its opening move, which is the one turn whose result can be reused
        # across games -- see the opening cache in `partition.py`.
        self._answers = 0

    @property
    def candidate_indices(self) -> tuple[CodeIndex, ...]:
        """Surviving candidates as positions in `all_candidates(ruleset)`.

        The index ordering *is* the grid ordering DESIGN.md lays cells out in,
        so the visualisation and the API want these and not symbols. Handing
        them out directly keeps the mapping in one place: a caller that got
        `Code` tuples and needed positions would have to rebuild a
        code-to-position table, which is exactly the side table this layer
        deleted by working in indices to begin with.

        Plain `int`s, so the tuple serialises to JSON with no conversion, even
        when the partitioner behind it is storing a numpy array.
        """
        if self._index_snapshot is None:
            self._index_snapshot = tuple(CodeIndex(int(i)) for i in self._indices)
        return self._index_snapshot

    @property
    def candidates(self) -> tuple[Code, ...]:
        """Codes still consistent with every answer so far.

        Never empty -- an answer that would empty it raises instead. A tuple
        rather than a list, so callers genuinely cannot mutate solver state
        through it, and cached until the next answer so repeated reads are free
        and always return the same object.

        Built lazily. The grid path reads `candidate_indices` and never touches
        this, so narrowing does not pay to turn a few thousand indices back into
        symbols nobody asked for.
        """
        if self._code_snapshot is None:
            self._code_snapshot = tuple(self._space[i] for i in self._indices)
        return self._code_snapshot

    @property
    def guess_pool(self) -> tuple[Code, ...]:
        """The codes this solver will consider guessing this turn."""
        return tuple(self._space[i] for i in self._pool)

    @property
    def _pool(self) -> CandidateSet:
        """The same pool as indices, which is what the search actually walks."""
        return self._indices if self.restrict_to_candidates else self._universe

    def guess(self) -> Code:
        """The next code to try. Does not change the solver's state."""
        return self._choose()

    def update(self, guess: Code, feedback: Feedback) -> None:
        """Narrow the candidate set by one answer.

        Raises:
            InconsistentFeedbackError: If no candidate survives, which means an
                earlier answer contradicts this one.
        """
        survivors = self._partitioner.block(
            self._index_of[guess], self._indices, feedback
        )
        if not survivors:
            raise InconsistentFeedbackError(
                f"no code can answer {feedback} to {''.join(guess)} and still "
                f"match every earlier answer; one of them must be wrong"
            )
        self._indices = survivors
        self._survivor_set = set(survivors)
        # Invalidate rather than rebuild: whichever view the caller asks for
        # next is the only one that gets built, and neither is built at all if
        # nobody asks.
        self._index_snapshot = None
        self._code_snapshot = None
        self._answers += 1

    def _partition(self, guess: CodeIndex) -> Sequence[int]:
        """Sizes of the groups this guess would split the survivors into.

        Every candidate produces exactly one feedback for a given guess, so the
        groups partition the surviving set and their sizes sum to it. How good a
        guess is depends only on the shape of that split, never on which
        feedback produced which group -- which is why the three scoring solvers
        can share this and differ by one line.
        """
        return self._partitioner.sizes(guess, self._indices)

    @abstractmethod
    def _choose(self) -> Code:
        """Pick a guess. The one thing a strategy has to supply."""
