"""Phase 5: the feedback matrix, and proof it changes nothing but speed."""

import numpy as np
import pytest
from hypothesis import given, settings

from guesstimate.core import (
    Code,
    Feedback,
    Ruleset,
    all_candidates,
    feedback_space,
    score,
)
from guesstimate.data import MatrixPartitioner, build_matrix, matrix_path
from guesstimate.solvers import SOLVERS, BaseSolver, Partitioner, PurePartitioner
from guesstimate.solvers.partitioner import CodeIndex

from .strategies import rulesets

SMALL = Ruleset(3, "12345")  # 60 codes
TINY = Ruleset(2, "1234")  # 12 codes


# --- the matrix itself -----------------------------------------------------


def test_the_matrix_is_square_over_the_candidate_space():
    matrix = build_matrix(SMALL)
    assert matrix.shape == (SMALL.space_size, SMALL.space_size)


def test_the_matrix_is_uint8():
    # One byte per pair is what makes 3024x3024 fit in 9 MB rather than 73.
    assert build_matrix(SMALL).dtype == np.uint8


def test_every_entry_is_the_scored_feedback():
    ruleset = TINY
    matrix = build_matrix(ruleset)
    space = all_candidates(ruleset)
    outcomes = feedback_space(ruleset)
    for guess_index, guess in enumerate(space):
        for candidate_index, candidate in enumerate(space):
            expected = score(candidate, guess)
            assert outcomes[matrix[guess_index, candidate_index]] == expected


def test_the_matrix_is_symmetric():
    # score(a, b) == score(b, a), which is why only half of it is computed.
    matrix = build_matrix(SMALL)
    assert np.array_equal(matrix, matrix.T)


def test_the_diagonal_is_the_win():
    ruleset = SMALL
    matrix = build_matrix(ruleset)
    win = feedback_space(ruleset).index(Feedback(ruleset.length, 0))
    assert np.all(np.diag(matrix) == win)


def test_outcome_indices_stay_inside_the_feedback_space():
    ruleset = SMALL
    matrix = build_matrix(ruleset)
    assert matrix.max() < len(feedback_space(ruleset))


@given(rulesets(max_space=40))
@settings(deadline=None, max_examples=15)
def test_the_matrix_agrees_with_scoring_for_any_ruleset(ruleset):
    matrix = build_matrix(ruleset)
    space = all_candidates(ruleset)
    outcomes = feedback_space(ruleset)
    for guess_index in range(len(space)):
        for candidate_index in range(len(space)):
            assert outcomes[matrix[guess_index, candidate_index]] == score(
                space[candidate_index], space[guess_index]
            )


# --- caching ---------------------------------------------------------------


def test_the_cache_key_is_stable_across_processes():
    # Python hashes strings with a per-process salt, so a filename derived from
    # hash() would change every run and the cache would never hit. This is the
    # regression guard for that: the name must be a pure function of the rules.
    assert matrix_path(SMALL).name == matrix_path(Ruleset(3, "12345")).name


def test_different_rulesets_get_different_files():
    names = {
        matrix_path(Ruleset(3, "12345")).name,
        matrix_path(Ruleset(4, "12345")).name,
        matrix_path(Ruleset(3, "123456")).name,
        matrix_path(Ruleset(3, "12345", allow_repeats=True)).name,
    }
    assert len(names) == 4


def test_a_cached_matrix_is_reused(tmp_path):
    first = MatrixPartitioner(SMALL, cache_dir=tmp_path)
    assert matrix_path(SMALL, tmp_path).exists()
    second = MatrixPartitioner(SMALL, cache_dir=tmp_path)
    assert np.array_equal(first.matrix, second.matrix)


def test_a_corrupt_cache_is_rebuilt_rather_than_trusted(tmp_path):
    # A run killed mid-write leaves a truncated .npy. That has already happened
    # once in this project, to a benchmark sweep.
    MatrixPartitioner(SMALL, cache_dir=tmp_path)
    path = matrix_path(SMALL, tmp_path)
    path.write_bytes(b"not an npy file")
    rebuilt = MatrixPartitioner(SMALL, cache_dir=tmp_path)
    assert rebuilt.matrix.shape == (SMALL.space_size, SMALL.space_size)


def test_a_cache_for_the_wrong_shape_is_rebuilt(tmp_path):
    MatrixPartitioner(SMALL, cache_dir=tmp_path)
    np.save(matrix_path(SMALL, tmp_path), np.zeros((3, 3), dtype=np.uint8))
    rebuilt = MatrixPartitioner(SMALL, cache_dir=tmp_path)
    assert rebuilt.matrix.shape == (SMALL.space_size, SMALL.space_size)


# --- the equivalence gate --------------------------------------------------
#
# The matrix is only allowed to exist if it changes speed and nothing else.
# These compare it against PurePartitioner, which is the reference
# implementation and the TypeScript port target.


@pytest.mark.parametrize("ruleset", [TINY, SMALL], ids=["12-codes", "60-codes"])
def test_both_partitioners_report_the_same_block_sizes(ruleset, tmp_path):
    pure = PurePartitioner(ruleset)
    fast = MatrixPartitioner(ruleset, cache_dir=tmp_path)
    universe = pure.universe()
    for guess in range(ruleset.space_size):
        assert sorted(pure.sizes(CodeIndex(guess), universe)) == sorted(
            fast.sizes(CodeIndex(guess), fast.universe())
        )


@pytest.mark.parametrize("ruleset", [TINY, SMALL], ids=["12-codes", "60-codes"])
def test_both_partitioners_keep_the_same_block(ruleset, tmp_path):
    pure = PurePartitioner(ruleset)
    fast = MatrixPartitioner(ruleset, cache_dir=tmp_path)
    for guess in range(ruleset.space_size):
        for feedback in feedback_space(ruleset):
            expected = list(pure.block(CodeIndex(guess), pure.universe(), feedback))
            actual = [
                int(i) for i in fast.block(CodeIndex(guess), fast.universe(), feedback)
            ]
            assert actual == expected


@given(rulesets(max_space=40))
@settings(deadline=None, max_examples=15)
def test_the_partitioners_agree_for_any_ruleset(tmp_path_factory, ruleset):
    cache = tmp_path_factory.mktemp("matrix")
    pure = PurePartitioner(ruleset)
    fast = MatrixPartitioner(ruleset, cache_dir=cache)
    universe_pure, universe_fast = pure.universe(), fast.universe()
    assert [int(i) for i in universe_fast] == list(universe_pure)

    for guess in range(ruleset.space_size):
        index = CodeIndex(guess)
        assert sorted(pure.sizes(index, universe_pure)) == sorted(
            fast.sizes(index, universe_fast)
        )


def _transcript(
    solver_class: type[BaseSolver],
    ruleset: Ruleset,
    secret: Code,
    partitioner: Partitioner,
) -> list[Code]:
    """Every guess a solver makes, in order, not just the count."""
    solver = solver_class(ruleset, partitioner=partitioner)
    guesses: list[Code] = []
    for _ in range(ruleset.space_size + 1):
        guess = solver.guess()
        guesses.append(guess)
        feedback = score(secret, guess)
        if feedback.is_win(ruleset.length):
            return guesses
        solver.update(guess, feedback)
    raise AssertionError("solver never won")


@pytest.mark.parametrize("solver_name", ["minimax", "expected-size", "entropy"])
def test_solvers_play_identically_turn_by_turn(solver_name, tmp_path):
    # Transcripts, not outcomes. Two solvers can agree on every final answer
    # while diverging on intermediate choices, and that divergence means a
    # tie-break bug -- which would silently make benchmarks irreproducible
    # rather than making a test fail.
    from guesstimate.solvers import clear_opening_cache

    solver_class = SOLVERS[solver_name]
    fast = MatrixPartitioner(SMALL, cache_dir=tmp_path)
    for secret in all_candidates(SMALL):
        clear_opening_cache()
        slow_game = _transcript(solver_class, SMALL, secret, PurePartitioner(SMALL))
        clear_opening_cache()
        fast_game = _transcript(solver_class, SMALL, secret, fast)
        assert slow_game == fast_game, f"diverged on secret {''.join(secret)}"


@given(rulesets(max_space=40))
@settings(deadline=None, max_examples=10)
def test_solvers_play_identically_on_generated_rulesets(tmp_path_factory, ruleset):
    from guesstimate.solvers import clear_opening_cache

    cache = tmp_path_factory.mktemp("matrix")
    fast = MatrixPartitioner(ruleset, cache_dir=cache)
    secret = all_candidates(ruleset)[0]
    for solver_name in ("minimax", "entropy"):
        clear_opening_cache()
        slow_game = _transcript(
            SOLVERS[solver_name], ruleset, secret, PurePartitioner(ruleset)
        )
        clear_opening_cache()
        fast_game = _transcript(SOLVERS[solver_name], ruleset, secret, fast)
        assert slow_game == fast_game


def test_the_public_indices_stay_plain_ints_behind_the_matrix(tmp_path):
    # numpy scalars would sail through every test above and then fail to
    # serialise at the Phase 6 API boundary.
    solver = SOLVERS["entropy"](
        SMALL, partitioner=MatrixPartitioner(SMALL, cache_dir=tmp_path)
    )
    solver.update(("1", "2", "3"), Feedback(1, 0))
    for index in solver.candidate_indices:
        assert type(index) is int
