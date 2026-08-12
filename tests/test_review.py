"""Phase 8: what a move was worth, and whether the metric can be trusted."""

import random

import pytest

from guesstimate.core import Feedback, Ruleset, all_candidates, parse_code, score
from guesstimate.review import (
    Grade,
    bits_gained,
    expected_remaining,
    grade_for,
    review_game,
)
from guesstimate.solvers import SOLVERS, PurePartitioner, clear_opening_cache

SMALL = Ruleset(3, "12345")


# --- the corrected metric --------------------------------------------------


def test_expected_remaining_is_the_probability_weighted_size():
    # Four blocks of one from four candidates: whichever answer comes back,
    # one candidate stands. Except the winning one, after which none do.
    assert expected_remaining([1, 1, 1, 1], 4, wins=False) == pytest.approx(1.0)
    assert expected_remaining([1, 1, 1, 1], 4, wins=True) == pytest.approx(0.75)


def test_the_winning_block_counts_as_nothing_remaining():
    # The correction, on its own terms: the question is how many candidates are
    # still standing once the answer arrives, and after "all bulls" the answer
    # is none. Counting the winning candidate as remaining is simply wrong.
    with_win = expected_remaining([1, 3], 4, wins=True)
    without = expected_remaining([1, 3], 4, wins=False)
    assert without - with_win == pytest.approx(1 / 4)


def test_a_guess_that_can_win_beats_an_identical_one_that_cannot():
    # Same split, different only in whether the guess is still possible. The
    # one that could end the game has to score better.
    sizes = [1, 2, 3]
    assert expected_remaining(sizes, 6, wins=True) < expected_remaining(
        sizes, 6, wins=False
    )


def test_realized_elimination_can_rank_the_wrong_guess_first():
    """Why eliminated-count is colour and not the metric.

    Note what it is *not*: expected elimination is `total - expected_remaining`
    exactly, so ranking on that would be the same ranking. The problem is the
    *realized* count, which is what a player actually sees, and which depends
    on the block they happened to land in rather than on the guess.

    A lopsided guess can look spectacular on a lucky answer. Splitting twelve
    candidates into 1 and 11 removes eleven of them if the answer is the rare
    one -- more than an even 6/6 split removes on any answer -- while being
    much the worse guess, because the other eleven times out of twelve it
    removes one.
    """
    lopsided = expected_remaining([1, 11], 12, wins=False)
    even = expected_remaining([6, 6], 12, wins=False)
    assert even < lopsided  # the even guess is better

    luckiest_lopsided = 12 - 1  # landed in the singleton
    always_even = 12 - 6
    assert luckiest_lopsided > always_even  # yet it "eliminated" more


def test_more_blocks_beat_fewer_even_when_uneven():
    # The corollary, and a trap for anyone tidying this later: equal blocks
    # only minimise expected remaining for a *fixed* number of blocks. Seven
    # uneven blocks beat three equal ones, because splitting more ways is worth
    # more than splitting evenly.
    three_equal = expected_remaining([4, 4, 4], 12, wins=False)
    seven_uneven = expected_remaining([6, 1, 1, 1, 1, 1, 1], 12, wins=False)
    assert seven_uneven < three_equal


def test_bits_gained_peaks_on_an_even_split():
    assert bits_gained([3, 3, 3, 3], 12) > bits_gained([9, 1, 1, 1], 12)
    assert bits_gained([12], 12) == pytest.approx(0.0)


def test_bits_and_expected_remaining_agree_on_direction():
    even, lumpy = [4, 4, 4], [10, 1, 1]
    assert expected_remaining(even, 12, False) < expected_remaining(lumpy, 12, False)
    assert bits_gained(even, 12) > bits_gained(lumpy, 12)


# --- grading against the position ------------------------------------------


def test_a_move_is_graded_against_where_it_was_played():
    # A weak second guess leaves a worse third position. The third move is
    # judged against that worse position, not against the line the player can
    # no longer reach -- otherwise one mistake is charged twice.
    secret = parse_code("123", SMALL)
    weak = [parse_code(g, SMALL) for g in ("451", "452", "123")]
    turns = [(g, score(secret, g)) for g in weak]
    reviews = review_game(SMALL, turns)
    assert len(reviews) == 3
    # Whatever the second move cost, the third is measured from what survived.
    assert reviews[2].survivors_before == reviews[1].survivors_after


def test_the_review_reports_both_pools():
    secret = parse_code("123", SMALL)
    turns = [(parse_code("451", SMALL), score(secret, parse_code("451", SMALL)))]
    review = review_game(SMALL, turns)[0]
    # Grading uses candidates only; the wider pool is shown alongside so the
    # player can see when a probe would have been worth a turn.
    assert review.best_any_remaining <= review.best_candidate_remaining
    assert review.probe_advantage >= 0


def test_a_perfect_move_loses_nothing():
    reviews = review_game(
        SMALL,
        [(parse_code("123", SMALL), Feedback(3, 0))],
    )
    assert reviews[0].loss == pytest.approx(0.0)
    assert reviews[0].grade is Grade.BEST


def test_eliminated_is_reported_but_not_ranked_on():
    secret = parse_code("123", SMALL)
    guess = parse_code("451", SMALL)
    review = review_game(SMALL, [(guess, score(secret, guess))])[0]
    assert review.eliminated == review.survivors_before - review.survivors_after


# --- the bands, and whether they can be trusted ----------------------------


def test_the_bands_are_ordered():
    thresholds = [
        threshold
        for threshold, _ in __import__("guesstimate.review", fromlist=["BANDS"]).BANDS
    ]
    assert thresholds == sorted(thresholds)


def test_only_an_exactly_optimal_move_is_best():
    assert grade_for(0.0, 100) is Grade.BEST
    assert grade_for(0.4, 100) is not Grade.BEST


def test_grades_scale_with_the_position():
    # The same absolute loss means different things in different positions:
    # giving up 10 expected candidates out of 3,024 is a rounding error, and
    # giving up 40 out of 60 is the game.
    assert grade_for(10, 3024) is Grade.GOOD
    assert grade_for(40, 60) is Grade.BLUNDER
    # And the bands are relative, so identical shares grade identically
    # regardless of scale.
    assert grade_for(30.24, 3024) is grade_for(0.6, 60)


def test_a_settled_position_cannot_be_graded_badly():
    assert grade_for(0.0, 1) is Grade.BEST


@pytest.mark.slow
@pytest.mark.parametrize(
    ("solver", "worst_allowed"),
    [
        ("expected-size", Grade.BEST),
        ("entropy", Grade.INACCURACY),
        ("minimax", Grade.MISTAKE),
    ],
)
def test_the_solvers_grade_as_well_as_they_play(solver, worst_allowed):
    """The metric has to agree with strategies whose quality is known.

    If entropy shows blunders, the metric is wrong rather than the player.
    `expected-size` is the sharpest check and also the least surprising: the
    metric *is* its objective, so anything other than a perfect score would
    mean the review and the solver disagree about their own definition.
    """
    order = list(Grade)
    ceiling = order.index(worst_allowed)
    rng = random.Random(11)
    partitioner = PurePartitioner(SMALL)

    for secret in rng.sample(all_candidates(SMALL), 30):
        clear_opening_cache()
        engine = SOLVERS[solver](SMALL, partitioner=partitioner, rng=random.Random(3))
        turns = []
        for _ in range(SMALL.space_size):
            guess = engine.guess()
            feedback = score(secret, guess)
            turns.append((guess, feedback))
            if feedback.is_win(SMALL.length):
                break
            engine.update(guess, feedback)

        for review in review_game(SMALL, turns, partitioner):
            assert order.index(review.grade) <= ceiling, (
                f"{solver} graded {review.grade} on turn {review.turn}; "
                f"the metric is more likely wrong than the solver"
            )


@pytest.mark.slow
def test_random_play_spreads_across_the_bands():
    # The other half of the validation: bands that never fire are not bands.
    rng = random.Random(5)
    partitioner = PurePartitioner(SMALL)
    seen: set[Grade] = set()

    for secret in rng.sample(all_candidates(SMALL), 40):
        engine = SOLVERS["random"](SMALL, partitioner=partitioner, rng=rng)
        turns = []
        for _ in range(SMALL.space_size):
            guess = engine.guess()
            feedback = score(secret, guess)
            turns.append((guess, feedback))
            if feedback.is_win(SMALL.length):
                break
            engine.update(guess, feedback)
        seen.update(review.grade for review in review_game(SMALL, turns, partitioner))

    assert len(seen) >= 3, f"random play only ever graded {seen}"
    assert Grade.BEST in seen
