import pytest
from hypothesis import given

from guesstimate.core import Feedback, Ruleset, parse_code, score

from .strategies import rulesets_with_code, rulesets_with_two_codes


def _code(text: str) -> tuple[str, ...]:
    return tuple(text)


def test_the_readme_example():
    # secret 1234, guess 3264: the 2 and the 4 are placed, the 3 is misplaced.
    assert score(_code("1234"), _code("3264")) == Feedback(2, 1)


@pytest.mark.parametrize(
    ("secret", "guess", "expected"),
    [
        ("1234", "1234", (4, 0)),
        ("1234", "4321", (0, 4)),
        ("1234", "5678", (0, 0)),
        ("1234", "1243", (2, 2)),
        ("1234", "1567", (1, 0)),
    ],
)
def test_known_scores(secret, guess, expected):
    assert score(_code(secret), _code(guess)) == Feedback(*expected)


@pytest.mark.parametrize(
    ("secret", "guess", "expected"),
    [
        # Where the naive pairwise double-loop goes wrong.
        ("1123", "1213", (2, 2)),
        ("1111", "1234", (1, 0)),
        ("1234", "1111", (1, 0)),
        ("1122", "2211", (0, 4)),
        ("1112", "1121", (2, 2)),
    ],
)
def test_scores_with_repeated_symbols(secret, guess, expected):
    # The default ruleset forbids repeats, but the scorer must be right anyway.
    assert score(_code(secret), _code(guess)) == Feedback(*expected)


def test_length_mismatch_is_an_error():
    with pytest.raises(ValueError, match="length"):
        score(_code("1234"), _code("123"))


@given(rulesets_with_two_codes())
def test_bulls_plus_cows_never_exceeds_length(case):
    ruleset, secret, guess = case
    feedback = score(secret, guess)
    assert feedback.bulls + feedback.cows <= ruleset.length


@given(rulesets_with_code())
def test_scoring_a_code_against_itself_is_all_bulls(case):
    ruleset, code = case
    assert score(code, code) == Feedback(ruleset.length, 0)


@given(rulesets_with_two_codes())
def test_scoring_is_symmetric(case):
    # Both halves count symbol agreement, which does not care which side is
    # which. Solvers rely on this to score a guess against a candidate.
    _, secret, guess = case
    assert score(secret, guess) == score(guess, secret)


@given(rulesets_with_two_codes())
def test_one_off_with_a_cow_is_impossible(case):
    # The (length - 1, 1) hole. See the proof in core/candidates.py.
    ruleset, secret, guess = case
    assert score(secret, guess) != Feedback(ruleset.length - 1, 1)


@given(rulesets_with_two_codes())
def test_only_an_exact_match_wins(case):
    ruleset, secret, guess = case
    assert score(secret, guess).is_win(ruleset.length) == (secret == guess)


def test_parsed_codes_score_the_same_as_raw_tuples():
    ruleset = Ruleset()
    assert score(parse_code("1234", ruleset), parse_code("3264", ruleset)) == Feedback(
        2, 1
    )
