"""Phase 5: the partitioner boundary."""

from hypothesis import given, settings

from guesstimate.core import Feedback, Ruleset, all_candidates, score
from guesstimate.solvers.partitioner import CodeIndex, PurePartitioner

from .strategies import rulesets

SMALL = Ruleset(3, "12345")  # 60 codes


def _pure(ruleset: Ruleset) -> PurePartitioner:
    return PurePartitioner(ruleset)


def test_universe_is_every_code_in_candidate_order():
    part = _pure(SMALL)
    universe = part.universe()
    assert len(universe) == SMALL.space_size
    assert [part.code(i) for i in universe] == all_candidates(SMALL)


def test_universe_returns_a_fresh_set_each_call():
    # It is a method, not a property, precisely because it may allocate. A
    # caller that narrows one copy must not narrow the other.
    part = _pure(SMALL)
    first, second = part.universe(), part.universe()
    assert list(first) == list(second)


def test_sizes_partition_the_candidate_set():
    part = _pure(SMALL)
    universe = part.universe()
    sizes = part.sizes(CodeIndex(0), universe)
    assert sum(sizes) == len(universe)


def test_sizes_match_scoring_by_hand():
    part = _pure(SMALL)
    universe = part.universe()
    guess = CodeIndex(7)
    by_hand: dict[Feedback, int] = {}
    for index in universe:
        feedback = score(part.code(index), part.code(guess))
        by_hand[feedback] = by_hand.get(feedback, 0) + 1
    assert sorted(part.sizes(guess, universe)) == sorted(by_hand.values())


def test_block_keeps_exactly_the_consistent_candidates():
    part = _pure(SMALL)
    universe = part.universe()
    guess = CodeIndex(3)
    feedback = Feedback(1, 0)
    kept = set(part.block(guess, universe, feedback))
    for index in universe:
        consistent = score(part.code(index), part.code(guess)) == feedback
        assert (index in kept) == consistent


def test_block_of_a_win_is_the_guess_alone():
    part = _pure(SMALL)
    guess = CodeIndex(11)
    kept = part.block(guess, part.universe(), Feedback(3, 0))
    assert list(kept) == [guess]


def test_block_can_be_empty_when_an_answer_contradicts():
    # "+0-0" over a 3-of-5 ruleset is impossible: it rules out three of five
    # symbols, leaving two to fill three distinct positions.
    part = _pure(SMALL)
    narrowed = part.block(CodeIndex(0), part.universe(), Feedback(0, 0))
    assert list(narrowed) == []


def test_blocks_of_every_outcome_reassemble_the_whole_set():
    from guesstimate.core import feedback_space

    part = _pure(SMALL)
    universe = part.universe()
    guess = CodeIndex(5)
    total = sum(
        len(part.block(guess, universe, feedback)) for feedback in feedback_space(SMALL)
    )
    assert total == len(universe)


@given(rulesets(max_space=60))
@settings(deadline=None, max_examples=30)
def test_sizes_and_blocks_agree_for_any_ruleset(ruleset):
    part = _pure(ruleset)
    universe = part.universe()
    guess = CodeIndex(0)
    sizes = sorted(part.sizes(guess, universe))

    from guesstimate.core import feedback_space

    blocks = sorted(
        len(part.block(guess, universe, feedback))
        for feedback in feedback_space(ruleset)
    )
    assert sizes == [n for n in blocks if n]


@given(rulesets(max_space=60))
@settings(deadline=None, max_examples=30)
def test_narrowing_twice_is_narrowing_the_narrowed(ruleset):
    # block() must work on any candidate set, not only the universe -- the
    # solver hands it the survivors of the previous turn.
    part = _pure(ruleset)
    universe = part.universe()
    secret = universe[len(universe) // 2]

    survivors = universe
    for guess in (CodeIndex(0), universe[-1]):
        feedback = score(part.code(secret), part.code(guess))
        survivors = part.block(guess, survivors, feedback)
        assert secret in survivors
        assert set(survivors) <= set(universe)


def test_a_code_index_is_not_just_any_integer():
    # CodeIndex is a NewType, so it is an int at runtime -- the guard is mypy,
    # not the interpreter. This records the intent for a reader who wonders
    # why the annotation exists at all.
    assert CodeIndex(3) == 3
    assert isinstance(CodeIndex(3), int)
