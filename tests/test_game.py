"""Phase 6: the game interface, and the local implementations behind it."""

import random

import pytest

from guesstimate.core import Feedback, Ruleset, all_candidates, score
from guesstimate.game import (
    Game,
    GameOverError,
    LocalCodebreakerGame,
    LocalRaceGame,
    LocalWatchGame,
    ObservedGame,
    RacedGame,
    ScoredGame,
    Secret,
    SecretHidden,
    SecretNever,
    SecretRevealed,
    SolverBackedGame,
)
from guesstimate.solvers import InconsistentFeedbackError

SMALL = Ruleset(3, "12345")


# --- which mode satisfies which protocol -----------------------------------
#
# The split is on two capabilities, not one. Whether a game can score a guess
# and whether it has a solver are independent, and watch mode has the second
# without the first -- there the secret is in the player's head, so the game
# cannot score a code it is handed.


def _has(obj: object, *names: str) -> bool:
    return all(hasattr(obj, name) for name in names)


def test_codebreaker_is_a_scored_game_with_no_solver():
    game = LocalCodebreakerGame(SMALL, rng=random.Random(0))
    assert _has(game, "state", "candidate_indices", "guess")
    assert not _has(game, "solver_guess")


def test_watch_has_a_solver_and_cannot_score():
    # The point of the two-axis split. A single-chain hierarchy would have
    # forced this mode to implement `guess` as a method that can only raise.
    game = LocalWatchGame(SMALL, rng=random.Random(0))
    assert _has(game, "state", "candidate_indices", "solver_guess", "submit_feedback")
    assert not _has(game, "guess")


def test_race_has_both():
    game = LocalRaceGame(SMALL, rng=random.Random(0))
    assert _has(game, "guess", "solver_guess")


@pytest.mark.parametrize(
    ("factory", "protocols"),
    [
        (LocalCodebreakerGame, (Game, ScoredGame)),
        (LocalWatchGame, (Game, SolverBackedGame, ObservedGame)),
        (LocalRaceGame, (Game, ScoredGame, SolverBackedGame, RacedGame)),
    ],
    ids=["codebreaker", "watch", "race"],
)
def test_each_mode_structurally_satisfies_its_protocols(factory, protocols):
    game = factory(SMALL, rng=random.Random(0))
    for protocol in protocols:
        for name in protocol.__protocol_attrs__:
            assert hasattr(game, name), f"{factory.__name__} lacks {name}"


# --- the secret is discriminated, not overloaded ---------------------------


def test_a_hidden_secret_is_not_a_missing_one():
    # `Code | None` conflated "withheld" with "never existed". Evil mode needs
    # the second and a reveal screen has to tell them apart.
    game = LocalCodebreakerGame(SMALL, secret=("1", "2", "3"))
    assert isinstance(game.state.secret, SecretHidden)
    assert not isinstance(game.state.secret, SecretNever)


def test_the_secret_appears_only_once_the_game_is_over():
    game = LocalCodebreakerGame(SMALL, secret=("1", "2", "3"))
    game.guess(("4", "5", "1"))
    assert isinstance(game.state.secret, SecretHidden)

    game.guess(("1", "2", "3"))
    revealed = game.state.secret
    assert isinstance(revealed, SecretRevealed)
    assert revealed.code == ("1", "2", "3")


def test_the_three_secret_states_are_distinguishable():
    # mypy rejects comparing two of these directly -- "non-overlapping equality"
    # -- which is the discrimination working at type level: a reveal screen
    # cannot confuse withheld with never-existed even by accident.
    states: list[Secret] = [
        SecretHidden(),
        SecretRevealed(("1", "2", "3")),
        SecretNever(),
    ]
    assert len({type(state) for state in states}) == 3
    for state in states:
        if isinstance(state, SecretRevealed):
            assert state.code == ("1", "2", "3")
        else:
            assert not hasattr(state, "code")


# --- codebreaker -----------------------------------------------------------


def test_a_correct_guess_wins():
    game = LocalCodebreakerGame(SMALL, secret=("1", "2", "3"))
    result = game.guess(("1", "2", "3"))
    assert result.feedback == Feedback(3, 0)
    assert result.finished and game.state.won


def test_a_wrong_guess_narrows_the_candidates():
    game = LocalCodebreakerGame(SMALL, secret=("1", "2", "3"))
    before = len(game.candidate_indices())
    result = game.guess(("4", "5", "1"))
    assert result.surviving < before
    assert len(game.candidate_indices()) == result.surviving


def test_the_board_records_every_turn_in_order():
    game = LocalCodebreakerGame(SMALL, secret=("1", "2", "3"))
    game.guess(("4", "5", "1"))
    game.guess(("1", "2", "3"))
    assert [turn.guess for turn in game.state.turns] == [
        ("4", "5", "1"),
        ("1", "2", "3"),
    ]


def test_playing_on_after_the_end_is_refused():
    game = LocalCodebreakerGame(SMALL, secret=("1", "2", "3"))
    game.guess(("1", "2", "3"))
    with pytest.raises(GameOverError):
        game.guess(("4", "5", "1"))


def test_candidate_indices_address_the_grid_order():
    space = all_candidates(SMALL)
    game = LocalCodebreakerGame(SMALL, secret=("1", "2", "3"))
    game.guess(("4", "5", "1"))
    for index in game.candidate_indices():
        assert score(space[index], ("4", "5", "1")) == game.state.turns[0].feedback


def test_the_same_seed_gives_the_same_secret():
    first = LocalCodebreakerGame(SMALL, rng=random.Random(4))
    second = LocalCodebreakerGame(SMALL, rng=random.Random(4))
    first.guess(("1", "2", "3"))
    second.guess(("1", "2", "3"))
    assert first.state.turns[0].feedback == second.state.turns[0].feedback


# --- watch -----------------------------------------------------------------


def test_the_solver_proposes_without_committing():
    game = LocalWatchGame(SMALL, rng=random.Random(0))
    assert game.solver_guess() == game.solver_guess()
    assert game.state.turns == ()


def test_answering_advances_the_game():
    game = LocalWatchGame(SMALL, rng=random.Random(0))
    secret = ("5", "4", "3")
    guess = game.solver_guess()
    result = game.submit_feedback(score(secret, guess))
    assert game.state.turns[0].guess == guess
    assert result.surviving < SMALL.space_size


def test_a_watched_game_can_be_won():
    game = LocalWatchGame(SMALL, rng=random.Random(0))
    secret = ("5", "4", "3")
    for _ in range(SMALL.space_size):
        guess = game.solver_guess()
        result = game.submit_feedback(score(secret, guess))
        if result.finished:
            break
    assert game.state.won
    revealed = game.state.secret
    assert isinstance(revealed, SecretRevealed) and revealed.code == secret


def test_contradictory_feedback_leaves_the_game_playable():
    # The CLI already treats this as recoverable; the interface must too.
    game = LocalWatchGame(SMALL, rng=random.Random(0))
    guess = game.solver_guess()
    game.submit_feedback(score(("5", "4", "3"), guess))
    before = len(game.candidate_indices())

    # "+0-0" is impossible on a 3-of-5 ruleset: it rules out three of the five
    # symbols, leaving two to fill three distinct positions.
    with pytest.raises(InconsistentFeedbackError):
        game.submit_feedback(Feedback(0, 0))

    assert len(game.candidate_indices()) == before
    assert not game.state.finished
    assert game.solver_guess() is not None


def test_answering_a_finished_watch_game_is_refused():
    game = LocalWatchGame(SMALL, rng=random.Random(0))
    game.submit_feedback(Feedback(3, 0))
    with pytest.raises(GameOverError):
        game.submit_feedback(Feedback(0, 0))


# --- race ------------------------------------------------------------------


def test_both_sides_play_the_same_secret():
    game = LocalRaceGame(SMALL, secret=("1", "2", "3"), rng=random.Random(0))
    player = game.guess(("4", "5", "1"))
    solver = game.play_solver_turn()
    assert player.feedback == score(("1", "2", "3"), ("4", "5", "1"))
    assert solver.feedback == score(("1", "2", "3"), game.solver_turns[0].guess)


def test_the_two_boards_stay_separate():
    game = LocalRaceGame(SMALL, secret=("1", "2", "3"), rng=random.Random(0))
    game.guess(("4", "5", "1"))
    game.play_solver_turn()
    assert len(game.state.turns) == 1
    assert len(game.solver_turns) == 1


def test_the_solver_can_win_the_race():
    game = LocalRaceGame(SMALL, secret=("1", "2", "3"), rng=random.Random(0))
    for _ in range(SMALL.space_size):
        if game.play_solver_turn().finished:
            break
    assert game.solver_turns[-1].feedback == Feedback(3, 0)


# --- nothing here knows about a server -------------------------------------


def test_the_local_game_imports_nothing_web_shaped():
    # Rule 10's actual content: anything assuming a round trip, a session id,
    # or a server clock is a RemoteGame detail and must not appear here.
    # Checked by imports rather than by grepping source, because the docstrings
    # in these modules discuss sessions at length in order to disclaim them.
    import ast
    import inspect

    from guesstimate.game import local, protocol

    allowed_roots = {"guesstimate", "dataclasses", "typing", "random", "abc"}
    for module in (local, protocol):
        tree = ast.parse(inspect.getsource(module))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    continue  # relative, so within this package by definition
                roots = [(node.module or "").split(".")[0]]
            else:
                continue
            for root in roots:
                if root in {"", "__future__"}:
                    continue
                assert root in allowed_roots, (
                    f"{module.__name__} imports {root}, which the shared game "
                    f"layer must not depend on"
                )


def test_a_contradictory_win_claim_is_rejected():
    # Watch mode's nastiest input: the player says the solver got it, on a code
    # that cannot be the secret given what they already said. Skipping the
    # solver update on wins would wave that through as a victory.
    #
    # It can only arise with an unrestricted solver. A restricted one only ever
    # guesses codes that are still possible, so claiming a win on its guess is
    # always consistent -- which is why the guard is easy to omit and hard to
    # notice missing.
    secret = ("5", "4", "3")
    game = LocalWatchGame(SMALL, rng=random.Random(0), restrict_to_candidates=False)
    for _ in range(SMALL.space_size):
        guess = game.solver_guess()
        possible = {all_candidates(SMALL)[i] for i in game.candidate_indices()}
        if guess not in possible:
            with pytest.raises(InconsistentFeedbackError):
                game.submit_feedback(Feedback(3, 0))
            assert not game.state.finished
            return
        result = game.submit_feedback(score(secret, guess))
        if result.finished:
            break
    pytest.skip("the unrestricted solver never proposed a ruled-out code")
