"""Phase 2: the four strategies and the interface they share."""

import inspect
import random
import statistics

import pytest

from guesstimate.core import Code, Feedback, Ruleset, all_candidates, score
from guesstimate.solvers import (
    SOLVERS,
    BaseSolver,
    EntropySolver,
    ExpectedSizeSolver,
    InconsistentFeedbackError,
    MinimaxSolver,
    RandomSolver,
    Solver,
    clear_opening_cache,
)
from guesstimate.solvers.partition import _OPENING_CACHE

SOLVER_CLASSES = [RandomSolver, MinimaxSolver, ExpectedSizeSolver, EntropySolver]
SOLVER_IDS = ["random", "minimax", "expected-size", "entropy"]

# 60 candidates. Big enough that the strategies visibly disagree, small enough
# that the naive O(n^2) sweep is instant -- the classic 3024 game is left to the
# slow-marked tests at the bottom.
SMALL = Ruleset(3, "12345")


def play(solver: Solver, secret: Code, limit: int = 25) -> int:
    """Drive a solver to the win, returning the number of guesses it took."""
    turns = 0
    while True:
        turns += 1
        guess = solver.guess()
        feedback = score(secret, guess)
        solver.update(guess, feedback)
        assert secret in solver.candidates, "the secret was eliminated"
        assert solver.candidates, "the candidate set emptied"
        if feedback.is_win(len(secret)):
            return turns
        assert turns < limit, f"no win after {limit} guesses"


# --- conformance -----------------------------------------------------------
#
# The protocol is not runtime_checkable on purpose: an isinstance() check
# against a Protocol only looks for method *names*, so a solver whose update()
# took the wrong number of arguments would sail through it. These compare real
# signatures instead.


@pytest.mark.parametrize("solver_class", SOLVER_CLASSES, ids=SOLVER_IDS)
@pytest.mark.parametrize("method", ["guess", "update"])
def test_method_signatures_match_the_protocol(solver_class, method):
    expected = inspect.signature(getattr(Solver, method))
    actual = inspect.signature(getattr(solver_class, method))
    assert actual == expected


@pytest.mark.parametrize("solver_class", SOLVER_CLASSES, ids=SOLVER_IDS)
def test_candidates_is_a_read_only_property(solver_class):
    assert isinstance(inspect.getattr_static(solver_class, "candidates"), property)
    assert inspect.getattr_static(solver_class, "candidates").fset is None


@pytest.mark.parametrize("solver_class", SOLVER_CLASSES, ids=SOLVER_IDS)
def test_constructors_are_uniform(solver_class):
    # The CLI --solver flag and the API build any strategy the same way; a
    # fifth solver must not force either of them to special-case it.
    assert inspect.signature(solver_class.__init__) == inspect.signature(
        BaseSolver.__init__
    )


def test_the_registry_lists_every_strategy():
    assert set(SOLVERS.values()) == set(SOLVER_CLASSES)
    assert sorted(SOLVERS) == sorted(SOLVER_IDS)


# --- shared behaviour ------------------------------------------------------


@pytest.mark.parametrize("solver_class", SOLVER_CLASSES, ids=SOLVER_IDS)
def test_starts_with_the_whole_space(solver_class):
    assert list(solver_class(SMALL).candidates) == all_candidates(SMALL)


@pytest.mark.parametrize("solver_class", SOLVER_CLASSES, ids=SOLVER_IDS)
def test_solves_every_secret(solver_class):
    for secret in all_candidates(SMALL):
        play(solver_class(SMALL, rng=random.Random(0)), secret)


@pytest.mark.parametrize("solver_class", SOLVER_CLASSES, ids=SOLVER_IDS)
def test_guessing_does_not_mutate_state(solver_class):
    solver = solver_class(SMALL, rng=random.Random(0))
    before = list(solver.candidates)
    solver.guess()
    assert list(solver.candidates) == before


@pytest.mark.parametrize("solver_class", SOLVER_CLASSES, ids=SOLVER_IDS)
def test_deterministic_solvers_repeat_their_guess(solver_class):
    solver = solver_class(SMALL, rng=random.Random(0))
    if isinstance(solver, RandomSolver):
        pytest.skip("RandomSolver re-samples by design")
    assert solver.guess() == solver.guess()


@pytest.mark.parametrize("solver_class", SOLVER_CLASSES, ids=SOLVER_IDS)
def test_contradictory_feedback_is_rejected(solver_class):
    solver = solver_class(SMALL, rng=random.Random(0))
    solver.update(("1", "2", "3"), Feedback(3, 0))  # claims 123 is the secret
    with pytest.raises(InconsistentFeedbackError):
        solver.update(("4", "5", "1"), Feedback(3, 0))  # and now claims 451 is


@pytest.mark.parametrize("solver_class", SOLVER_CLASSES, ids=SOLVER_IDS)
def test_a_rejected_answer_leaves_the_solver_untouched(solver_class):
    solver = solver_class(SMALL, rng=random.Random(0))
    solver.update(("1", "2", "3"), Feedback(1, 0))
    before = list(solver.candidates)

    with pytest.raises(InconsistentFeedbackError):
        solver.update(("1", "2", "3"), Feedback(3, 0))

    # Still playable: the CLI offers a correction rather than restarting.
    assert list(solver.candidates) == before
    assert solver.guess() in solver.candidates


@pytest.mark.parametrize("solver_class", SOLVER_CLASSES, ids=SOLVER_IDS)
def test_a_foreign_guess_is_accepted(solver_class):
    # Race mode scores a human's guess against the solver's own state.
    solver = solver_class(SMALL, rng=random.Random(0))
    secret = ("5", "4", "3")
    solver.update(("1", "2", "3"), score(secret, ("1", "2", "3")))
    assert secret in solver.candidates


# --- strategy-specific -----------------------------------------------------


def test_random_ignores_the_restrict_flag():
    # Documented behaviour: an unrestricted random guess cannot win, which
    # would make the v1 baseline meaningless.
    solver = RandomSolver(SMALL, restrict_to_candidates=False, rng=random.Random(1))
    solver.update(("1", "2", "3"), Feedback(1, 0))
    assert len(solver.candidates) < SMALL.space_size
    for _ in range(50):
        assert solver.guess() in solver.candidates


def test_random_is_reproducible_from_a_seed():
    first = [RandomSolver(SMALL, rng=random.Random(7)).guess() for _ in range(3)]
    assert len(set(first)) == 1


def test_minimax_opening_minimises_the_worst_bucket():
    solver = MinimaxSolver(SMALL)
    opening = solver.guess()
    worst = max(_bucket_sizes(SMALL, opening, all_candidates(SMALL)))
    for other in all_candidates(SMALL):
        assert worst <= max(_bucket_sizes(SMALL, other, all_candidates(SMALL)))


def _bucket_sizes(ruleset: Ruleset, guess: Code, candidates: list[Code]) -> list[int]:
    counts: dict[Feedback, int] = {}
    for candidate in candidates:
        feedback = score(candidate, guess)
        counts[feedback] = counts.get(feedback, 0) + 1
    return list(counts.values())


def test_entropy_cost_is_negated_so_that_lower_means_more_information():
    # The primary guard on the sign flip, and the only exact one. Shannon
    # entropy of n equal groups is log2(n) bits, and _cost returns its
    # negation, so a split that reveals more must score *lower*.
    cost = EntropySolver(SMALL)._cost
    assert cost([1, 1, 1, 1]) == pytest.approx(-2.0)  # 2 bits
    assert cost([2, 2]) == pytest.approx(-1.0)  # 1 bit
    assert cost([4]) == pytest.approx(0.0)  # learns nothing
    assert cost([2, 2]) < cost([3, 1]) < cost([4])


# --- the opening cache -----------------------------------------------------
#
# Turn one is ~90% of a game's cost and its answer is identical every game, so
# it is computed once per (strategy, ruleset, restriction). The risk is not
# speed but silence: a cache keyed too loosely returns another ruleset's
# opening, and every test that only checks "the solver eventually wins" would
# still pass.


@pytest.fixture(autouse=True)
def _isolate_opening_cache():
    clear_opening_cache()
    yield
    clear_opening_cache()


@pytest.mark.parametrize(
    "solver_class", [MinimaxSolver, ExpectedSizeSolver, EntropySolver]
)
def test_the_cached_opening_is_what_the_search_would_have_returned(solver_class):
    uncached = solver_class(SMALL)._search()
    clear_opening_cache()
    assert solver_class(SMALL).guess() == uncached
    assert solver_class(SMALL).guess() == uncached  # now served from the cache


@pytest.mark.parametrize(
    "solver_class", [MinimaxSolver, ExpectedSizeSolver, EntropySolver]
)
def test_the_opening_is_cached_after_the_first_game(solver_class):
    assert not _OPENING_CACHE
    solver_class(SMALL).guess()
    assert list(_OPENING_CACHE) == [(solver_class, SMALL, True)]


def test_rulesets_and_restrictions_get_their_own_entries():
    other = Ruleset(3, "12345", allow_repeats=True)
    MinimaxSolver(SMALL).guess()
    MinimaxSolver(SMALL, restrict_to_candidates=False).guess()
    MinimaxSolver(other).guess()
    EntropySolver(SMALL).guess()
    assert set(_OPENING_CACHE) == {
        (MinimaxSolver, SMALL, True),
        (MinimaxSolver, SMALL, False),
        (MinimaxSolver, other, True),
        (EntropySolver, SMALL, True),
    }


def test_a_cached_opening_never_answers_for_a_later_turn():
    # Only turn one is fixed across games; reusing it afterwards would make the
    # solver replay its opening forever.
    solver = MinimaxSolver(SMALL)
    opening = solver.guess()
    solver.update(opening, Feedback(1, 0))
    assert solver.guess() != opening


def test_random_openings_still_vary_with_the_seed():
    # RandomSolver is not a PartitionSolver, so it is excluded by construction.
    # If the cache ever migrates up to BaseSolver, this is what catches it.
    openings = {RandomSolver(SMALL, rng=random.Random(s)).guess() for s in range(20)}
    assert len(openings) > 1
    assert not _OPENING_CACHE


def test_clearing_the_cache_empties_it():
    MinimaxSolver(SMALL).guess()
    assert _OPENING_CACHE
    clear_opening_cache()
    assert not _OPENING_CACHE


# The sweep below plays every secret in a 120-code ruleset with every solver.
# It is the "guess ceiling across a sampled sweep" Phase 2 calls for, and it is
# also where the end-to-end sign check lives, so the games are played once and
# shared.
#
# 120 codes rather than 60 is deliberate and measured. At 60, random-from-
# survivors is so nearly optimal that entropy's mean (3.283) exactly ties
# random's best seed, and the comparison is a coin flip. At 120 the ordering is
# stable: entropy 3.883, random 3.908-3.983 across eight seeds.
SWEEP = Ruleset(4, "12345")


@pytest.fixture(scope="module")
def sweep_results() -> dict[str, list[int]]:
    secrets = all_candidates(SWEEP)
    return {
        name: [play(cls(SWEEP, rng=random.Random(0)), secret) for secret in secrets]
        for name, cls in SOLVERS.items()
    }


@pytest.mark.slow
def test_no_solver_exceeds_the_guess_ceiling(sweep_results):
    # Measured worst case is 6 for all four. The ceiling is a regression guard
    # with one turn of headroom, not a published result -- Phase 3 owns those.
    for name, counts in sweep_results.items():
        assert max(counts) <= 7, f"{name} took {max(counts)} guesses"


@pytest.mark.slow
def test_entropy_beats_random_on_mean_guesses(sweep_results):
    # The end-to-end half of the sign check. It is a weaker guard than the
    # exact test above and deliberately kept anyway: a flipped sign still
    # produces a legal, terminating solver, so the only visible symptom is that
    # it plays worse. Measured means over all 120 secrets -- entropy 3.883,
    # sign-flipped 4.033, random 3.944 averaged over eight seeds -- so the flip
    # lands the wrong side of random and this fails.
    entropy = statistics.mean(sweep_results["entropy"])
    baselines = [
        statistics.mean(
            play(RandomSolver(SWEEP, rng=random.Random(seed)), secret)
            for secret in all_candidates(SWEEP)
        )
        for seed in range(8)
    ]
    assert entropy < statistics.mean(baselines)


@pytest.mark.slow
def test_expected_size_beats_random_on_mean_guesses(sweep_results):
    # Minimax is deliberately absent. It optimises the worst case, not the
    # mean, and measured over these 120 secrets its mean (3.933) is no better
    # than random's best seed (3.908). That is the strategy working as
    # designed, not a defect, so asserting otherwise would be wrong.
    expected_size = statistics.mean(sweep_results["expected-size"])
    baseline = statistics.mean(
        play(RandomSolver(SWEEP, rng=random.Random(seed)), secret)
        for seed in range(8)
        for secret in all_candidates(SWEEP)
    )
    assert expected_size < baseline


# --- tie-breaking ----------------------------------------------------------


def test_a_tie_between_a_candidate_and_a_non_candidate_picks_the_candidate():
    # The key sorts ascending, so "is a candidate" must be encoded as False to
    # come first. Encoding it as True silently prefers the non-candidate.
    ruleset = Ruleset(2, "1234")
    solver = MinimaxSolver(ruleset, restrict_to_candidates=False)
    solver.update(("1", "2"), Feedback(0, 0))

    costs = {
        guess: solver._cost(_bucket_sizes(ruleset, guess, list(solver.candidates)))
        for guess in solver.guess_pool
    }
    best = min(costs.values())
    tied = [guess for guess, cost in costs.items() if cost == best]
    survivors = set(solver.candidates)

    # The test is only meaningful if a non-candidate actually ties.
    assert any(guess not in survivors for guess in tied)
    assert any(guess in survivors for guess in tied)
    assert solver.guess() in survivors


def test_ties_among_candidates_go_to_the_earliest_in_alphabet_order():
    ruleset = Ruleset(2, "1234")
    solver = MinimaxSolver(ruleset)
    order = all_candidates(ruleset)

    costs = {
        guess: solver._cost(_bucket_sizes(ruleset, guess, list(solver.candidates)))
        for guess in solver.guess_pool
    }
    best = min(costs.values())
    tied = [guess for guess, cost in costs.items() if cost == best]
    assert len(tied) > 1, "no tie to break"
    assert solver.guess() == min(tied, key=order.index)
