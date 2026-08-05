"""Full games played through the engine alone.

No solver yet -- Phase 2 owns those. The "strategy" here is to guess any
surviving candidate at random, which is what the original script did, and it is
enough to prove the engine can carry a game from first guess to win.
"""

import random

from hypothesis import given
from hypothesis import strategies as st

from guesstimate.core import Code, Ruleset, all_candidates, filter_candidates, score

from .strategies import classic_codes, rulesets


def play(ruleset: Ruleset, secret: Code, rng: random.Random) -> list[int]:
    """Play a game out, returning the surviving count after each guess."""
    survivors = all_candidates(ruleset)
    counts: list[int] = []
    while True:
        before = len(survivors)
        guess = rng.choice(survivors)
        feedback = score(secret, guess)
        survivors = filter_candidates(survivors, guess, feedback)
        counts.append(len(survivors))

        # The secret is consistent with every answer it produced, so no filter
        # can ever remove it. If it does, scoring and filtering disagree.
        assert secret in survivors
        assert survivors, "the surviving set must never empty out"

        if feedback.is_win(ruleset.length):
            assert survivors == [secret]
            return counts

        # A losing guess is always eliminated by its own feedback, so the set
        # strictly shrinks and the game cannot run forever.
        assert len(survivors) < before


def test_a_full_game_on_the_classic_ruleset():
    counts = play(Ruleset(), ("4", "7", "1", "2"), random.Random(0))
    assert counts[-1] == 1
    assert counts[0] < 3024


def test_many_games_from_a_seeded_sweep():
    ruleset = Ruleset()
    rng = random.Random(1234)
    for secret in rng.sample(all_candidates(ruleset), 40):
        assert play(ruleset, secret, rng)[-1] == 1


def test_the_surviving_set_never_grows():
    counts = play(Ruleset(), ("9", "8", "7", "6"), random.Random(7))
    assert counts == sorted(counts, reverse=True)
    assert counts[-1] == 1


@given(rulesets(), st.randoms(use_true_random=False))
def test_the_secret_is_never_eliminated(ruleset, rng):
    secret = rng.choice(all_candidates(ruleset))
    assert play(ruleset, secret, rng)[-1] == 1


@given(classic_codes(), st.randoms(use_true_random=False))
def test_the_secret_is_never_eliminated_at_full_scale(secret, rng):
    # Both the secret and the guessing are generated, on the real 3024-code
    # game. The seeded games above are fixed regressions; this is the property.
    assert play(Ruleset(), secret, rng)[-1] == 1
