"""Replaying a finished game and scoring each move from where it was played."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from guesstimate.core import Code, Feedback, Ruleset
from guesstimate.solvers import Partitioner, PurePartitioner
from guesstimate.solvers.partitioner import CodeIndex

from .grades import Grade, grade_for
from .metrics import best_at, bits_gained, expected_remaining


@dataclass(frozen=True)
class MoveReview:
    """One guess, judged against what was available when it was made."""

    turn: int
    guess: Code
    feedback: Feedback
    survivors_before: int
    survivors_after: int
    #: Reported, never ranked on. How many codes a guess removes says nothing
    #: about the shape it leaves them in, and shape is what costs turns:
    #: removing 2,900 into one surviving lump is worse than removing 2,500 into
    #: even blocks, because the player does not choose which block they land in.
    eliminated: int
    expected_remaining: float
    bits_gained: float
    best_candidate_remaining: float
    best_any_remaining: float
    best_candidate: Code | None
    best_any: Code | None
    loss: float
    grade: Grade

    @property
    def probe_advantage(self) -> float:
        """What a non-candidate probe would have bought over the best candidate.

        Positive when guessing something that cannot win would have left fewer
        candidates. Shown rather than graded on -- it is the interesting part
        of the position, not a stick to beat the player with.
        """
        return self.best_candidate_remaining - self.best_any_remaining


def review_game(
    ruleset: Ruleset,
    turns: Sequence[tuple[Code, Feedback]],
    partitioner: Partitioner | None = None,
) -> list[MoveReview]:
    """Score every move in a finished game.

    Each move is judged against the position it was actually played from, not
    against the game's best possible line. A weak second guess leaves a worse
    third position, and grading the third against a tree the player can no
    longer reach would charge them twice for one mistake. Chess engines score
    against the board in front of you, and so does this.
    """
    engine = PurePartitioner(ruleset) if partitioner is None else partitioner
    space = engine.universe()
    survivors = engine.universe()

    reviews: list[MoveReview] = []
    for number, (guess, feedback) in enumerate(turns, start=1):
        before = len(survivors)
        index = CodeIndex(_position_of(engine, guess))
        alive = {int(i) for i in survivors}

        sizes = engine.sizes(index, survivors)
        value = expected_remaining(sizes, before, index in alive)
        bits = bits_gained(sizes, before)
        best = best_at(engine, survivors, space)

        survivors = engine.block(index, survivors, feedback)
        after = len(survivors)
        loss = value - best.among_candidates

        reviews.append(
            MoveReview(
                turn=number,
                guess=guess,
                feedback=feedback,
                survivors_before=before,
                survivors_after=after,
                eliminated=before - after,
                expected_remaining=value,
                bits_gained=bits,
                best_candidate_remaining=best.among_candidates,
                best_any_remaining=best.among_all,
                best_candidate=_code_at(engine, best.best_candidate),
                best_any=_code_at(engine, best.best_any),
                loss=loss,
                grade=grade_for(loss, before),
            )
        )
    return reviews


def _position_of(engine: Partitioner, code: Code) -> int:
    from guesstimate.core import all_candidates

    ruleset = getattr(engine, "ruleset", None)
    if ruleset is None:
        raise ValueError("partitioner does not expose its ruleset")
    return all_candidates(ruleset).index(code)


def _code_at(engine: Partitioner, index: CodeIndex | None) -> Code | None:
    if index is None:
        return None
    from guesstimate.core import all_candidates

    ruleset = getattr(engine, "ruleset", None)
    if ruleset is None:
        return None
    return all_candidates(ruleset)[index]
