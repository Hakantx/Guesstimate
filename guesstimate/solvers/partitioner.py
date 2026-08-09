"""How a solver asks what a guess would do to the candidate set."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import NewType, Protocol

from guesstimate.core import Code, Feedback, Ruleset, all_candidates, score

CodeIndex = NewType("CodeIndex", int)
"""A code's position in `all_candidates(ruleset)`.

A `NewType` rather than a bare `int` because this ordering is load-bearing in
four separate places -- the solver tie-break, the DESIGN.md grid layout, and
both axes of the feedback matrix -- and every one of them silently produces
plausible-looking wrong answers if an integer from somewhere else arrives
instead. It costs nothing at runtime and cannot be retrofitted once callers
exist.
"""

CandidateSet = Sequence[CodeIndex]
"""A set of still-possible codes, as indices.

Deliberately not a set of `Code` tuples. The matrix-backed partitioner needs
integer indices to slice rows with, and converting on every call would put the
conversion inside the loop this phase exists to speed up.
"""


class Partitioner(Protocol):
    """Groups candidates by the feedback a guess would draw from each.

    A guess splits the candidate set into blocks, one per possible answer. That
    single idea covers both things a solver needs: ranking a guess reads the
    sizes of every block, and narrowing after an answer keeps exactly one of
    them. Filtering is not a separate operation -- it is picking the block the
    answer names.

    Two implementations. `PurePartitioner` scores on demand and is the
    reference: it is what the TypeScript port transcribes, and it is the oracle
    the matrix-backed one is checked against. The matrix-backed one lives in
    `guesstimate/data/` because it needs numpy and a cache file, neither of
    which belongs under `solvers/`.
    """

    def universe(self) -> CandidateSet:
        """Every code in the ruleset, in candidate order.

        A method rather than a property: the returned type is up to the
        implementation and may allocate, and a property would imply cheap
        attribute access.
        """
        ...

    def sizes(self, guess: CodeIndex, candidates: CandidateSet) -> Sequence[int]:
        """Block sizes of the partition `guess` induces on `candidates`.

        Order carries no meaning -- every strategy here judges a split by the
        shape of its block sizes, never by which answer produced which block.
        The sizes sum to `len(candidates)`.
        """
        ...

    def block(
        self, guess: CodeIndex, candidates: CandidateSet, feedback: Feedback
    ) -> CandidateSet:
        """The single block whose answer is `feedback` -- the survivors.

        Empty when the feedback contradicts an earlier answer; the caller is
        responsible for noticing and refusing.
        """
        ...


class PurePartitioner:
    """Scores on demand, with no precomputation and no dependencies.

    The straightforward implementation: to find out what a guess does to a
    candidate, score the two. It is quadratic per turn and that is the point --
    it is the thing the feedback matrix is measured against, and it stays in the
    tree and under test rather than living in git history.

    It is also the reference implementation in two other senses. It is what the
    TypeScript port transcribes for offline play, and it is the oracle for the
    matrix-backed partitioner's equivalence tests.
    """

    def __init__(self, ruleset: Ruleset) -> None:
        self.ruleset = ruleset
        self._space = tuple(all_candidates(ruleset))

    def code(self, index: CodeIndex) -> Code:
        """The code at an index. The only place indices become symbols again."""
        return self._space[index]

    def universe(self) -> CandidateSet:
        """Every index, in candidate order."""
        return [CodeIndex(i) for i in range(len(self._space))]

    def sizes(self, guess: CodeIndex, candidates: CandidateSet) -> Sequence[int]:
        """Score the guess against every candidate and count the answers."""
        counts: Counter[Feedback] = Counter(
            score(self._space[index], self._space[guess]) for index in candidates
        )
        return list(counts.values())

    def block(
        self, guess: CodeIndex, candidates: CandidateSet, feedback: Feedback
    ) -> CandidateSet:
        """Keep the candidates that would have produced this answer."""
        guess_code = self._space[guess]
        return [
            index
            for index in candidates
            if score(self._space[index], guess_code) == feedback
        ]
