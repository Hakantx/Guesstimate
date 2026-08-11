"""How much the greedy adversary gives up, measured exhaustively.

The mirror of the solver-side result. There, greedy play costs a full guess
against a published worst-case optimum for the 5040 variant. Here there is no
published optimum for an adversary, so it is computed: on rulesets small enough
to search exhaustively, what could a perfect adversary force?
"""

import pytest

from guesstimate.core import Ruleset, all_candidates
from guesstimate.game import LocalEvilGame

from .gametree import Tree

# (ruleset, what an optimal adversary forces, what the greedy one forces)
MEASURED = [
    (Ruleset(2, "123"), 3, 3),
    (Ruleset(2, "1234"), 3, 3),
    (Ruleset(2, "12345"), 4, 4),
    (Ruleset(2, "1234", allow_repeats=True), 4, 4),
    (Ruleset(3, "1234"), 4, 4),
    (Ruleset(3, "123", allow_repeats=True), 4, 3),  # the one with a gap
]
IDS = ["2of3", "2of4", "2of5", "2of4-rep", "3of4", "3of3-rep"]


@pytest.mark.parametrize(("ruleset", "optimal", "greedy"), MEASURED, ids=IDS)
def test_the_greedy_adversary_matches_its_measured_value(ruleset, optimal, greedy):
    tree = Tree(ruleset)
    assert tree.against_optimal() == optimal
    assert tree.against_greedy() == greedy


def test_greedy_is_usually_optimal_and_sometimes_not():
    # Eight of nine rulesets searched showed no gap at all, so the headline is
    # not "greedy is bad" -- it is that greedy is *usually* perfect here and
    # occasionally is not, which is only visible by computing the alternative.
    gaps = {
        ids: optimal - greedy
        for ids, (_, optimal, greedy) in zip(IDS, MEASURED, strict=True)
    }
    assert gaps["3of3-rep"] == 1
    assert all(gap == 0 for name, gap in gaps.items() if name != "3of3-rep")


def test_the_model_agrees_with_the_shipped_adversary():
    # The value above describes `LocalEvilGame` only if the search models the
    # same adversary. This plays the real one along the computed best line and
    # checks it takes exactly as long as predicted.
    for ruleset, _, greedy in MEASURED:
        tree = Tree(ruleset)
        game = LocalEvilGame(ruleset)
        space = all_candidates(ruleset)

        for turn in range(1, ruleset.space_size + 2):
            alive = tuple(space[i] for i in game.candidate_indices())
            if game.guess(tree.best_line(alive)).finished:
                assert turn == greedy, f"{ruleset}: took {turn}, predicted {greedy}"
                break
        else:
            raise AssertionError(f"{ruleset}: never finished")


@pytest.mark.slow
def test_the_gap_holds_on_larger_searches():
    # Slow because the optimal search is exponential in the space. 60 codes is
    # about the edge of what is worth waiting for.
    for ruleset, expected in ((Ruleset(3, "12345"), 4), (Ruleset(4, "1234"), 5)):
        tree = Tree(ruleset)
        assert tree.against_optimal() == expected
        assert tree.against_greedy() == expected
