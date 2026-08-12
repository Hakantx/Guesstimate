"""Phase 8: what a move was worth, and whether the metric can be trusted."""

import math
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


# --- worked by hand --------------------------------------------------------


def test_a_position_computed_on_paper():
    """The check the solver cross-check structurally cannot make.

    `expected-size` scoring a perfect 100% shows the review and the solver
    agree. It cannot show they are both right, because the metric *is* that
    solver's objective -- if both implemented the same wrong definition, the
    agreement would be exactly as clean. So one position is worked out by hand.

    Ruleset: two positions over the symbols 1, 2, 3, no repeats. Six codes:

        12  13  21  23  31  32

    Guess `12`. Scoring each candidate against it by hand:

        12 -> +2-0   both digits in place                 (the win)
        13 -> +1-0   the 1 is in place, the 3 is absent
        32 -> +1-0   the 2 is in place, the 3 is absent
        21 -> +0-2   both digits present, both misplaced
        23 -> +0-1   the 2 is present but misplaced
        31 -> +0-1   the 1 is present but misplaced

    Four blocks: {12}, {13, 32}, {21}, {23, 31} -- sizes 1, 2, 1, 2, summing to
    the six candidates.

        expected remaining = (2^2 + 1^2 + 2^2) / 6 = 9 / 6 = 1.5

    The winning block contributes nothing, which is the whole correction: after
    "+2-0" there is no candidate left to face. Including it would give 10/6,
    about 1.667, and would be answering a different question.

        bits gained = -[2*(1/6)log2(1/6) + 2*(2/6)log2(2/6)]
                    = (1/3)*log2(6) + (2/3)*log2(3)
                    = 0.8617 + 1.0566 = 1.9183
    """
    ruleset = Ruleset(2, "123")
    guess = parse_code("12", ruleset)

    blocks: dict[Feedback, int] = {}
    for candidate in all_candidates(ruleset):
        outcome = score(candidate, guess)
        blocks[outcome] = blocks.get(outcome, 0) + 1

    assert sorted(blocks.values()) == [1, 1, 2, 2]
    assert sum(blocks.values()) == 6

    sizes = list(blocks.values())
    assert expected_remaining(sizes, 6, wins=True) == pytest.approx(1.5)
    assert expected_remaining(sizes, 6, wins=False) == pytest.approx(10 / 6)

    expected_bits = (1 / 3) * math.log2(6) + (2 / 3) * math.log2(3)
    assert bits_gained(sizes, 6) == pytest.approx(expected_bits)
    assert bits_gained(sizes, 6) == pytest.approx(1.9183, abs=1e-4)


# --- caching ---------------------------------------------------------------


def test_the_cache_is_keyed_on_the_transcript_not_the_game():
    # Analysis is a pure function of what the player was told, so two games
    # with different secrets that produced the same answers are one analysis.
    from guesstimate.review import ReviewCache, transcript_key

    turns = [(parse_code("123", SMALL), Feedback(1, 0))]
    assert transcript_key(SMALL, turns) == transcript_key(SMALL, list(turns))
    assert transcript_key(SMALL, turns) != transcript_key(Ruleset(3, "123456"), turns)

    cache = ReviewCache()
    first = review_game(SMALL, turns, cache=cache)
    assert cache.misses >= 1
    second = review_game(SMALL, turns, cache=cache)
    assert cache.hits >= 1
    assert [r.loss for r in first] == [r.loss for r in second]


def test_two_games_share_the_positions_they_have_in_common():
    # The level that actually pays: every game on a ruleset opens from the same
    # position, and transcripts that diverge later still share what came before.
    from guesstimate.review import ReviewCache

    cache = ReviewCache()
    opening = parse_code("123", SMALL)
    review_game(SMALL, [(opening, Feedback(1, 0))], cache=cache)
    searched = len(cache._positions)

    # A different game with the same opening: the opening position is not
    # searched again.
    review_game(SMALL, [(opening, Feedback(0, 1))], cache=cache)
    assert len(cache._positions) >= searched
    positions_after_one_more = len(cache._positions)
    review_game(SMALL, [(opening, Feedback(2, 0))], cache=cache)
    assert len(cache._positions) == positions_after_one_more, (
        "a third game with the same opening searched a position again"
    )


def test_caching_changes_nothing_but_speed():
    from guesstimate.review import ReviewCache

    secret = parse_code("541", SMALL)
    turns = []
    for text in ("123", "245", "541"):
        guess = parse_code(text, SMALL)
        turns.append((guess, score(secret, guess)))

    plain = review_game(SMALL, turns)
    cached = review_game(SMALL, turns, cache=ReviewCache())
    assert [(r.loss, r.grade, r.expected_remaining) for r in plain] == [
        (r.loss, r.grade, r.expected_remaining) for r in cached
    ]


def test_the_cache_is_bounded():
    from guesstimate.review import ReviewCache

    cache = ReviewCache(max_entries=4)
    for n in range(20):
        cache.remember((n, "x", False, ()), [])
        cache.remember_position((n,), (0.0, 0.0, None, None))
    assert len(cache._reviews) <= 4
    assert len(cache._positions) <= 4
