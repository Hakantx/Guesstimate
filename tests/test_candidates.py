import itertools

from hypothesis import given

from guesstimate.core import (
    Feedback,
    Ruleset,
    all_candidates,
    feedback_space,
    filter_candidates,
    score,
)

from .strategies import (
    SPACE_HEAVY_MAX_SPACE,
    classic_codes,
    rulesets,
    rulesets_with_two_codes,
)

CLASSIC_CANDIDATES = all_candidates(Ruleset())


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


@given(rulesets(max_space=SPACE_HEAVY_MAX_SPACE))
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
def test_the_outcomes_partition_the_candidate_space(ruleset):
    # Every candidate lands in exactly one bucket, so the parts sum to the whole.
    candidates = all_candidates(ruleset)
    guess = candidates[0]
    total = sum(
        len(filter_candidates(candidates, guess, feedback))
        for feedback in feedback_space(ruleset)
    )
    assert total == len(candidates)
