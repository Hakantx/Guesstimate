import itertools

import pytest
from hypothesis import given, settings

from guesstimate.core import (
    Code,
    Feedback,
    Ruleset,
    all_candidates,
    feedback_space,
    filter_candidates,
    relabelling_representatives,
    score,
)

from .strategies import (
    SPACE_HEAVY_MAX_SPACE,
    classic_codes,
    rulesets,
    rulesets_with_two_codes,
)

CLASSIC_CANDIDATES = all_candidates(Ruleset())

# These tests score a whole candidate space per example, so their runtime moves
# with coverage instrumentation and machine load -- Hypothesis's 200ms deadline
# tripped intermittently under `pytest --cov`. Dropping it costs nothing: the
# shortcut they exercise is pinned by value in
# test_the_relabelling_shortcut_stays_a_shortcut, not by how long it takes.
SPACE_HEAVY = settings(deadline=None)


def test_the_classic_game_has_3024_candidates():
    assert len(all_candidates(Ruleset())) == 3024


def test_candidates_follow_alphabet_order():
    # DESIGN.md lays the grid out in this order; it must not drift.
    candidates = all_candidates(Ruleset())
    assert candidates[0] == ("1", "2", "3", "4")
    assert candidates[1] == ("1", "2", "3", "5")
    assert candidates[-1] == ("9", "8", "7", "6")


def test_candidates_with_repeats_are_a_product():
    candidates = all_candidates(Ruleset(length=2, alphabet="123", allow_repeats=True))
    assert candidates[0] == ("1", "1")
    assert len(candidates) == 9
    assert ("2", "2") in candidates


@given(rulesets())
def test_candidate_count_matches_space_size(ruleset):
    assert len(all_candidates(ruleset)) == ruleset.space_size


@given(rulesets())
def test_candidates_are_unique_and_well_formed(ruleset):
    candidates = all_candidates(ruleset)
    assert len(set(candidates)) == len(candidates)
    for code in candidates:
        assert len(code) == ruleset.length
        assert all(symbol in ruleset.alphabet for symbol in code)
        if not ruleset.allow_repeats:
            assert len(set(code)) == ruleset.length


def test_the_classic_game_has_14_outcomes():
    space = feedback_space(Ruleset())
    assert len(space) == 14


def test_three_bulls_one_cow_is_not_an_outcome():
    assert Feedback(3, 1) not in feedback_space(Ruleset())


def test_feedback_space_is_sorted_and_deduplicated():
    # Phase 5 encodes outcomes as an index into this list, so the order is API.
    space = feedback_space(Ruleset())
    assert space == sorted(space, key=lambda fb: (fb.bulls, fb.cows))
    assert len(set(space)) == len(space)


@given(rulesets(max_space=60))
@SPACE_HEAVY
def test_feedback_space_matches_brute_force(ruleset):
    # feedback_space only scores a few representative secrets, leaning on the
    # relabelling argument. This checks that shortcut against every pair, which
    # is why the rulesets here are kept tiny.
    candidates = all_candidates(ruleset)
    brute = {
        score(secret, guess)
        for secret, guess in itertools.product(candidates, repeat=2)
    }
    assert set(feedback_space(ruleset)) == brute


# feedback_space scores one secret per relabelling class instead of every
# secret. That is a correctness optimization, so it needs correctness tests: the
# two below pin the answer against full brute force at a size where the shortcut
# is doing real work, and pin the size of the shortcut itself.
#
# Both halves are load-bearing. Equality alone cannot detect the filter being
# switched off, because scoring every secret produces the same set -- just far
# more slowly. Only the representative counts catch that, and they catch it by
# value rather than by a timing deadline that drifts with the hardware.

MID_SIZE = [
    # Ruleset, and how many relabelling classes it has. Sizes were picked by
    # timing the brute force rather than by estimating it: the quadratic sweep
    # runs at about 5us per pair once set-building is counted, so these land at
    # 0.3s, 1.3s, and 1.9s. A 1680-code ruleset took 14s and was cut.
    (Ruleset(5, "123", allow_repeats=True), 41),  # partitions of 5 into <=3, 243 codes
    (Ruleset(3, "123456789"), 1),  # no repeats: one all-distinct pattern, 504 codes
    (Ruleset(4, "12345", allow_repeats=True), 15),  # Bell(4), 625 codes
]
MID_SIZE_IDS = ["243-codes-repeats", "504-codes-no-repeats", "625-codes-repeats"]


@pytest.mark.slow
@pytest.mark.parametrize("ruleset", [case[0] for case in MID_SIZE], ids=MID_SIZE_IDS)
def test_feedback_space_matches_brute_force_at_mid_size(ruleset):
    candidates = all_candidates(ruleset)
    brute = {
        score(secret, guess)
        for secret, guess in itertools.product(candidates, repeat=2)
    }
    assert set(feedback_space(ruleset)) == brute


@pytest.mark.parametrize(("ruleset", "representatives"), MID_SIZE, ids=MID_SIZE_IDS)
def test_the_relabelling_shortcut_stays_a_shortcut(ruleset, representatives):
    # Exact counts, because they are the combinatorics the optimization rests
    # on: one class when every code is all-distinct, otherwise the number of
    # ways to partition the positions into at most len(alphabet) groups.
    found = relabelling_representatives(ruleset)
    assert len(found) == representatives
    assert len(found) < ruleset.space_size
    # Every representative is a real candidate, and no two are relabellings of
    # each other -- distinct symbol patterns, whatever the symbols happen to be.
    assert set(found) <= set(all_candidates(ruleset))
    assert len({_pattern(code) for code in found}) == len(found)


def _pattern(code: Code) -> tuple[int, ...]:
    """The shape of a code with the symbol names thrown away: 2231 -> 0012."""
    order: dict[str, int] = {}
    for symbol in code:
        if symbol not in order:
            order[symbol] = len(order)
    return tuple(order[symbol] for symbol in code)


def test_the_classic_game_is_a_single_relabelling_class():
    # Every one of the 3024 codes is four distinct symbols, so they are all
    # relabellings of 1234 and feedback_space scores exactly one secret.
    assert relabelling_representatives(Ruleset()) == [("1", "2", "3", "4")]


@given(rulesets(max_space=SPACE_HEAVY_MAX_SPACE))
@SPACE_HEAVY
def test_every_candidate_is_a_relabelling_of_exactly_one_representative(ruleset):
    # The classes have to cover the space, or feedback_space misses outcomes.
    patterns = {_pattern(code) for code in relabelling_representatives(ruleset)}
    for code in all_candidates(ruleset):
        assert _pattern(code) in patterns


@given(rulesets(max_space=SPACE_HEAVY_MAX_SPACE))
@SPACE_HEAVY
def test_every_space_contains_the_win_and_excludes_the_hole(ruleset):
    space = feedback_space(ruleset)
    assert Feedback(ruleset.length, 0) in space
    assert Feedback(ruleset.length - 1, 1) not in space


@given(rulesets_with_two_codes())
def test_the_secret_always_survives_its_own_feedback(case):
    ruleset, secret, guess = case
    feedback = score(secret, guess)
    survivors = filter_candidates(all_candidates(ruleset), guess, feedback)
    assert secret in survivors


@given(rulesets_with_two_codes())
def test_survivors_are_exactly_the_consistent_candidates(case):
    ruleset, secret, guess = case
    feedback = score(secret, guess)
    survivors = set(filter_candidates(all_candidates(ruleset), guess, feedback))
    for candidate in all_candidates(ruleset):
        assert (candidate in survivors) == (score(candidate, guess) == feedback)


@given(classic_codes(), classic_codes())
def test_the_secret_survives_at_full_scale(secret, guess):
    # Same property as above, on the 3024-code game the bounded ruleset
    # strategy can never reach.
    feedback = score(secret, guess)
    assert secret in filter_candidates(CLASSIC_CANDIDATES, guess, feedback)


@given(classic_codes())
def test_a_winning_guess_leaves_only_the_secret(secret):
    assert filter_candidates(CLASSIC_CANDIDATES, secret, Feedback(4, 0)) == [secret]


@given(rulesets(max_space=SPACE_HEAVY_MAX_SPACE))
@SPACE_HEAVY
def test_the_outcomes_partition_the_candidate_space(ruleset):
    # Every candidate lands in exactly one bucket, so the parts sum to the whole.
    candidates = all_candidates(ruleset)
    guess = candidates[0]
    total = sum(
        len(filter_candidates(candidates, guess, feedback))
        for feedback in feedback_space(ruleset)
    )
    assert total == len(candidates)
