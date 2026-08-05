import dataclasses

import pytest
from hypothesis import given

from guesstimate.core import Feedback, score

from .strategies import (
    classic_codes,
    feedbacks,
    rulesets_with_reachable_feedback,
)


def test_renders_in_plus_minus_form():
    assert str(Feedback(2, 1)) == "+2-1"
    assert str(Feedback(0, 0)) == "+0-0"


def test_parses_plus_minus_form():
    assert Feedback.parse("+2-1") == Feedback(bulls=2, cows=1)


def test_surrounding_whitespace_is_tolerated():
    assert Feedback.parse("  +2-1 ") == Feedback(2, 1)


def test_multi_digit_counts_round_trip():
    # Length is a parameter; a length-12 ruleset must not break the format.
    assert Feedback.parse("+10-2") == Feedback(10, 2)
    assert str(Feedback(10, 2)) == "+10-2"


@pytest.mark.parametrize(
    "text",
    ["", "  ", "21", "+21", "2-1", "+2-", "-2-1", "+a-1", "+2-b", "+2-1-0", "++2-1"],
)
def test_rejects_malformed_feedback(text):
    with pytest.raises(ValueError, match="feedback"):
        Feedback.parse(text)


def test_rejects_negative_counts():
    with pytest.raises(ValueError, match="negative"):
        Feedback(-1, 0)


def test_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        Feedback(1, 1).bulls = 2  # type: ignore[misc]


def test_is_hashable():
    # Solvers partition candidates into a dict keyed by feedback.
    assert len({Feedback(2, 1), Feedback(2, 1), Feedback(1, 2)}) == 2


def test_win_is_all_bulls():
    assert Feedback(4, 0).is_win(4) is True
    assert Feedback(3, 0).is_win(4) is False
    assert Feedback(3, 1).is_win(4) is False
    # A shorter ruleset wins at a different number -- never hardcode 4.
    assert Feedback(3, 0).is_win(3) is True


@given(feedbacks())
def test_parse_inverts_str(feedback):
    assert Feedback.parse(str(feedback)) == feedback


@given(rulesets_with_reachable_feedback())
def test_parse_inverts_str_for_reachable_outcomes(case):
    # The ruleset is generated too, so this is not an enumeration of one fixed
    # feedback space -- it round-trips outcomes drawn from many different games.
    _, feedback = case
    assert Feedback.parse(str(feedback)) == feedback


@given(classic_codes(), classic_codes())
def test_parse_inverts_str_on_real_scores(case, guess):
    # Round-trips feedback that came out of the scorer rather than a constructor.
    assert Feedback.parse(str(score(case, guess))) == score(case, guess)


@given(feedbacks(), feedbacks())
def test_equality_is_by_value(first, second):
    assert (first == second) == (
        (first.bulls, first.cows) == (second.bulls, second.cows)
    )
