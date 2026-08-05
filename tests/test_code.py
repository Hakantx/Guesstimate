import pytest
from hypothesis import given

from guesstimate.core import Ruleset, format_code, parse_code

from .strategies import rulesets_with_code


def test_parses_to_a_tuple_of_symbols():
    # Not a string and not an int -- ints break on leading zeros and on hex.
    assert parse_code("1234", Ruleset()) == ("1", "2", "3", "4")


def test_surrounding_whitespace_is_tolerated():
    assert parse_code("  1234\n", Ruleset()) == ("1", "2", "3", "4")


def test_hex_alphabet_parses():
    ruleset = Ruleset(length=3, alphabet="0123456789ABCDEF")
    assert parse_code("A0F", ruleset) == ("A", "0", "F")


def test_leading_zeros_survive():
    # An int-backed code would render this as 123 and lose the game.
    ruleset = Ruleset(length=4, alphabet="0123456789")
    assert format_code(parse_code("0123", ruleset)) == "0123"


@pytest.mark.parametrize(
    ("text", "match"),
    [
        ("", "4 symbols"),
        ("   ", "4 symbols"),
        ("123", "4 symbols"),
        ("12345", "4 symbols"),
        ("1230", "not in the alphabet"),
        ("12X4", "not in the alphabet"),
        ("1123", "repeat"),
    ],
)
def test_rejects_bad_input(text, match):
    # The original crashed on an empty line. Nothing past here sees a raw string.
    with pytest.raises(ValueError, match=match):
        parse_code(text, Ruleset())


def test_repeats_accepted_when_the_ruleset_allows_them():
    ruleset = Ruleset(length=4, alphabet="123456789", allow_repeats=True)
    assert parse_code("1123", ruleset) == ("1", "1", "2", "3")


@given(rulesets_with_code())
def test_parse_and_format_round_trip(case):
    ruleset, code = case
    assert parse_code(format_code(code), ruleset) == code
