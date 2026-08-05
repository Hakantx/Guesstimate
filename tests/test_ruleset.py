import dataclasses

import pytest

from guesstimate.core import Ruleset


def test_defaults_are_the_classic_game():
    ruleset = Ruleset()
    assert ruleset.length == 4
    assert ruleset.alphabet == "123456789"
    assert ruleset.allow_repeats is False
    assert ruleset.space_size == 3024


def test_space_size_without_repeats_is_a_permutation_count():
    assert Ruleset(length=2, alphabet="123").space_size == 6
    assert Ruleset(length=3, alphabet="123").space_size == 6


def test_space_size_with_repeats_is_a_power():
    assert Ruleset(length=2, alphabet="123", allow_repeats=True).space_size == 9
    assert (
        Ruleset(length=4, alphabet="123456789", allow_repeats=True).space_size == 6561
    )


def test_hex_mode_is_just_a_different_alphabet():
    ruleset = Ruleset(length=4, alphabet="0123456789ABCDEF")
    assert ruleset.space_size == 16 * 15 * 14 * 13


def test_zeros_are_not_a_flag():
    # CLAUDE.md rule 3: zeros exist exactly when "0" is in the alphabet.
    assert "0" not in Ruleset().alphabet
    assert "0" in Ruleset(alphabet="0123456789").alphabet


def test_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        Ruleset().length = 5  # type: ignore[misc]


def test_is_hashable():
    # Phase 5 keys its matrix cache by ruleset; that needs a stable hash.
    assert len({Ruleset(), Ruleset(), Ruleset(length=5)}) == 2


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"length": 0}, "length"),
        ({"length": -1}, "length"),
        ({"alphabet": ""}, "alphabet"),
        ({"alphabet": "1123"}, "duplicate"),
        ({"alphabet": "12 3"}, "whitespace"),
        ({"length": 4, "alphabet": "123"}, "repeats"),
    ],
)
def test_rejects_impossible_rulesets(kwargs, match):
    with pytest.raises(ValueError, match=match):
        Ruleset(**kwargs)


def test_length_may_exceed_alphabet_when_repeats_are_allowed():
    assert Ruleset(length=4, alphabet="12", allow_repeats=True).space_size == 16
