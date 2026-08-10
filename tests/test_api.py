"""Phase 6: the routes, and proof the two Game implementations agree."""

import random
from collections.abc import Sequence
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from guesstimate.api import (
    ModeNotSupportedError,
    RateLimitedError,
    RateLimiter,
    RemoteGame,
    SessionStore,
    create_app,
)
from guesstimate.core import (
    Code,
    Feedback,
    Ruleset,
    all_candidates,
    format_code,
    score,
)
from guesstimate.game import (
    GameOverError,
    LocalCodebreakerGame,
    LocalWatchGame,
    ObservedGame,
    ScoredGame,
    SecretHidden,
    SecretRevealed,
)
from guesstimate.solvers import InconsistentFeedbackError

SMALL = Ruleset(3, "12345")
SMALL_BODY = {"length": 3, "alphabet": "12345", "allow_repeats": False}

#: (guess, feedback, surviving, next guess) for one watched turn.
_WatchRow = tuple[str, str, int, str | None]


@pytest.fixture
def client():
    with TestClient(create_app(SessionStore())) as test_client:
        yield test_client


def start(client: TestClient, **overrides: object) -> dict[str, Any]:
    body: dict[str, Any] = {"ruleset": SMALL_BODY, "seed": 7} | overrides
    response = client.post("/game", json=body)
    assert response.status_code == 201, response.text
    return dict(response.json())


# --- starting a game -------------------------------------------------------


def test_a_new_game_reports_the_whole_space_surviving(client):
    body = start(client)
    assert body["surviving"] == SMALL.space_size
    assert body["turns"] == []
    assert not body["finished"]


def test_the_secret_is_not_in_the_response(client):
    # The leak guard, checked on the wire rather than in the domain object.
    body = start(client, secret="123")
    assert body["secret"] == {"kind": "hidden", "code": None}
    assert "123" not in str(body["secret"])


def test_an_impossible_ruleset_is_rejected(client):
    response = client.post("/game", json={"ruleset": {"length": 5, "alphabet": "abc"}})
    assert response.status_code == 422


def test_an_unknown_solver_is_rejected(client):
    assert client.post("/game", json={"solver": "psychic"}).status_code == 422


def test_a_bad_fixed_secret_is_rejected(client):
    response = client.post("/game", json={"ruleset": SMALL_BODY, "secret": "999"})
    assert response.status_code == 422


# --- playing ---------------------------------------------------------------


def test_a_guess_is_scored(client):
    game_id = start(client, secret="123")["id"]
    body = client.post(f"/game/{game_id}/guess", json={"guess": "145"}).json()
    assert body["feedback"] == str(score(("1", "2", "3"), ("1", "4", "5")))
    assert body["surviving"] < SMALL.space_size


def test_winning_reveals_the_secret(client):
    game_id = start(client, secret="123")["id"]
    client.post(f"/game/{game_id}/guess", json={"guess": "123"})
    state = client.get(f"/game/{game_id}/state").json()
    assert state["finished"] and state["won"]
    assert state["secret"] == {"kind": "revealed", "code": "123"}


def test_playing_on_after_the_end_is_a_conflict(client):
    game_id = start(client, secret="123")["id"]
    client.post(f"/game/{game_id}/guess", json={"guess": "123"})
    response = client.post(f"/game/{game_id}/guess", json={"guess": "145"})
    assert response.status_code == 409


def test_a_malformed_guess_is_rejected(client):
    game_id = start(client, secret="123")["id"]
    for bad in ("", "12", "1234", "199", "abc"):
        response = client.post(f"/game/{game_id}/guess", json={"guess": bad})
        assert response.status_code == 422, bad


def test_candidates_are_grid_indices(client):
    game_id = start(client, secret="123")["id"]
    client.post(f"/game/{game_id}/guess", json={"guess": "145"})
    body = client.get(f"/game/{game_id}/candidates").json()
    assert body["total"] == SMALL.space_size
    space = all_candidates(SMALL)
    for index in body["indices"]:
        assert score(space[index], ("1", "4", "5")) == score(
            ("1", "2", "3"), ("1", "4", "5")
        )


def test_an_unknown_game_is_a_404(client):
    assert client.get("/game/nope/state").status_code == 404


# --- capability, enforced by the routes ------------------------------------


def test_watch_mode_refuses_a_guess(client):
    # The secret is in the player's head, so the server has nothing to check
    # it against. This is the two-axis protocol split showing up on the wire.
    game_id = start(client, mode="watch")["id"]
    response = client.post(f"/game/{game_id}/guess", json={"guess": "123"})
    assert response.status_code == 409
    assert "cannot score" in response.json()["detail"]


def test_codebreaker_mode_refuses_feedback(client):
    game_id = start(client, secret="123")["id"]
    response = client.post(f"/game/{game_id}/feedback", json={"feedback": "+1-0"})
    assert response.status_code == 409


def test_codebreaker_mode_has_no_solver(client):
    game_id = start(client, secret="123")["id"]
    assert client.get(f"/game/{game_id}/solver-guess").status_code == 409


# --- watch mode: one round trip per turn -----------------------------------


def test_the_answer_carries_the_next_guess(client):
    game_id = start(client, mode="watch")["id"]
    first = client.get(f"/game/{game_id}/solver-guess").json()["guess"]
    body = client.post(f"/game/{game_id}/feedback", json={"feedback": "+1-0"}).json()
    assert body["next_guess"] is not None
    assert body["next_guess"] != first


def test_a_watched_game_needs_no_extra_round_trips(client):
    # One call to open, then one call per turn. Anything more would mean the
    # next guess is not riding along with the answer.
    game_id = start(client, mode="watch")["id"]
    secret = ("5", "4", "3")
    guess = client.get(f"/game/{game_id}/solver-guess").json()["guess"]

    calls = 0
    for _ in range(SMALL.space_size):
        feedback = score(secret, tuple(guess))
        body = client.post(
            f"/game/{game_id}/feedback", json={"feedback": str(feedback)}
        ).json()
        calls += 1
        if body["finished"]:
            break
        guess = body["next_guess"]
    assert calls == len(client.get(f"/game/{game_id}/state").json()["turns"])


def test_contradictory_feedback_is_a_recoverable_conflict(client):
    game_id = start(client, mode="watch")["id"]
    client.get(f"/game/{game_id}/solver-guess")
    response = client.post(f"/game/{game_id}/feedback", json={"feedback": "+0-0"})
    assert response.status_code == 409
    assert response.json()["error"] == "inconsistent_feedback"
    # And the game survives it.
    assert client.get(f"/game/{game_id}/state").json()["finished"] is False


def test_malformed_feedback_is_rejected(client):
    game_id = start(client, mode="watch")["id"]
    for bad in ("", "nonsense", "+9", "2-1"):
        response = client.post(f"/game/{game_id}/feedback", json={"feedback": bad})
        assert response.status_code == 422, bad


# --- sessions --------------------------------------------------------------


def test_games_expire(client):
    ticks = [0.0]
    store = SessionStore(ttl_seconds=10, clock=lambda: ticks[0])
    with TestClient(create_app(store)) as fresh:
        game_id = fresh.post("/game", json={"ruleset": SMALL_BODY}).json()["id"]
        assert fresh.get(f"/game/{game_id}/state").status_code == 200
        ticks[0] = 11.0
        assert fresh.get(f"/game/{game_id}/state").status_code == 404


def test_activity_keeps_a_game_alive():
    ticks = [0.0]
    store = SessionStore(ttl_seconds=10, clock=lambda: ticks[0])
    with TestClient(create_app(store)) as fresh:
        game_id = fresh.post("/game", json={"ruleset": SMALL_BODY}).json()["id"]
        for _ in range(5):
            ticks[0] += 8.0
            assert fresh.get(f"/game/{game_id}/state").status_code == 200


def test_ids_are_unguessable(client):
    ids = {start(client)["id"] for _ in range(20)}
    assert len(ids) == 20
    assert all(len(i) >= 16 for i in ids)


# --- the equivalence gate --------------------------------------------------
#
# Until Phase 7 there would otherwise be exactly one implementation of `Game`,
# and a protocol with one implementation describes that implementation rather
# than the idea. These play the same seeded games both ways and compare
# transcripts turn by turn, not just outcomes.


def _codebreaker_transcript(
    game: ScoredGame, guesses: Sequence[Code]
) -> list[tuple[Code, str, int, bool]]:
    """Every (guess, feedback, surviving, finished) row, in order."""
    rows: list[tuple[Code, str, int, bool]] = []
    for code in guesses:
        result = game.guess(code)
        rows.append((code, str(result.feedback), result.surviving, result.finished))
        if result.finished:
            break
    return rows


def test_codebreaker_plays_identically_local_and_remote(client):
    secret = ("1", "2", "3")
    guesses = [("4", "5", "1"), ("1", "5", "2"), ("1", "2", "3")]

    local = LocalCodebreakerGame(SMALL, secret=secret)
    remote = RemoteGame.start(client, ruleset=SMALL, secret=secret, seed=7)

    assert _codebreaker_transcript(local, guesses) == (
        _codebreaker_transcript(remote, guesses)
    )


def test_seeded_secrets_agree_local_and_remote(client):
    # No fixed secret: both sides draw from the same seed, so the whole game
    # has to line up including which code was chosen.
    local = LocalCodebreakerGame(SMALL, rng=random.Random(11))
    remote = RemoteGame.start(client, ruleset=SMALL, seed=11)

    space = all_candidates(SMALL)
    local_rows = _codebreaker_transcript(local, space[:6])
    remote_rows = _codebreaker_transcript(remote, space[:6])
    assert local_rows == remote_rows


def test_watch_plays_identically_local_and_remote(client):
    secret = ("5", "4", "3")
    local = LocalWatchGame(SMALL, rng=random.Random(7))
    remote = RemoteGame.start(client, mode="watch", ruleset=SMALL, seed=7)

    local_rows: list[_WatchRow] = []
    remote_rows: list[_WatchRow] = []
    games: list[tuple[list[_WatchRow], ObservedGame]] = [
        (local_rows, local),
        (remote_rows, remote),
    ]
    for rows, game in games:
        guess: Code | None = game.solver_guess()
        for _ in range(SMALL.space_size):
            assert guess is not None
            result = game.submit_feedback(score(secret, guess))
            rows.append(
                (
                    format_code(guess),
                    str(result.feedback),
                    result.surviving,
                    None
                    if result.next_guess is None
                    else format_code(result.next_guess),
                )
            )
            if result.finished:
                break
            guess = result.next_guess
    assert local_rows == remote_rows


def test_both_implementations_report_the_same_candidate_indices(client):
    secret = ("1", "2", "3")
    local = LocalCodebreakerGame(SMALL, secret=secret)
    remote = RemoteGame.start(client, ruleset=SMALL, secret=secret, seed=7)
    for code in (("4", "5", "1"), ("1", "5", "2")):
        local.guess(code)
        remote.guess(code)
        assert local.candidate_indices() == remote.candidate_indices()


def test_both_implementations_hide_and_reveal_alike(client):
    secret = ("1", "2", "3")
    local = LocalCodebreakerGame(SMALL, secret=secret)
    remote = RemoteGame.start(client, ruleset=SMALL, secret=secret, seed=7)

    assert isinstance(local.state.secret, SecretHidden)
    assert isinstance(remote.state.secret, SecretHidden)

    local.guess(secret)
    remote.guess(secret)
    for state in (local.state, remote.state):
        assert isinstance(state.secret, SecretRevealed)
        assert state.secret.code == secret


def test_domain_errors_survive_the_wire(client):
    # A caller written against `Game` catches domain exceptions. It should not
    # also have to catch HTTP statuses to handle the same mistakes remotely.
    remote = RemoteGame.start(client, ruleset=SMALL, secret=("1", "2", "3"), seed=7)
    remote.guess(("1", "2", "3"))
    with pytest.raises(GameOverError):
        remote.guess(("4", "5", "1"))

    watching = RemoteGame.start(client, mode="watch", ruleset=SMALL, seed=7)
    watching.solver_guess()
    with pytest.raises(InconsistentFeedbackError):
        watching.submit_feedback(Feedback(0, 0))


def test_remote_satisfies_the_same_protocols(client):
    remote = RemoteGame.start(client, ruleset=SMALL, seed=7)
    assert isinstance(remote, ScoredGame)
    assert isinstance(remote, ObservedGame)


# --- what runtime_checkable does not check ---------------------------------


def test_isinstance_passes_a_wrong_arity_implementation():
    # The limitation, made executable rather than described. `runtime_checkable`
    # compares method *names* and nothing else, so this class satisfies
    # isinstance while being unusable: `guess` takes no code and `state` is not
    # even a property.
    #
    # That is precisely why the `Solver` protocol is not runtime_checkable --
    # there the question is conformance, and a name check answers the wrong
    # one. Here the question is "does this mode offer a guess at all", which is
    # what a name check is for. The distinction is the whole justification for
    # using it in one place and refusing it in the other.
    class Malformed:
        state = None

        def candidate_indices(self) -> tuple[int, ...]:
            return ()

        def guess(self) -> None:  # missing the code argument entirely
            return None

    broken: Any = Malformed()
    assert isinstance(broken, ScoredGame), "isinstance accepted a broken class"
    with pytest.raises(TypeError):
        broken.guess(("1", "2", "3"))


# --- error codes map one-to-one --------------------------------------------


def test_every_failure_carries_a_code(client):
    game_id = start(client, secret="123")["id"]
    cases = [
        (client.get("/game/nope/state"), "not_found"),
        (
            client.post(f"/game/{game_id}/guess", json={"guess": "zzz"}),
            "invalid",
        ),
        (
            client.post(f"/game/{game_id}/feedback", json={"feedback": "+1-0"}),
            "wrong_mode",
        ),
    ]
    for response, expected in cases:
        assert not response.is_success
        assert response.json()["error"] == expected, response.text


def test_the_client_maps_each_code_to_one_exception(client):
    from guesstimate.api.client import _ERRORS
    from guesstimate.api.schemas import ErrorCode

    declared = set(ErrorCode.__args__)  # type: ignore[attr-defined]
    assert set(_ERRORS) == declared, "every server code needs a client exception"
    assert len(set(_ERRORS.values())) == len(_ERRORS), "codes must not share one"


def test_an_unknown_code_is_loud_rather_than_guessed(client):
    from guesstimate.api.client import _raise_for

    response = httpx.Response(
        409, json={"error": "from_the_future", "detail": "who knows"}
    )
    with pytest.raises(RuntimeError, match="unrecognised error code"):
        _raise_for(response)


def test_wrong_mode_raises_its_own_exception(client):
    remote = RemoteGame.start(client, ruleset=SMALL, secret=("1", "2", "3"), seed=7)
    with pytest.raises(ModeNotSupportedError):
        remote.submit_feedback(Feedback(1, 0))


# --- what a public endpoint refuses --------------------------------------


def test_an_enormous_ruleset_is_refused(client):
    # The serious one. The server enumerates the whole candidate space to start
    # a game and the ruleset comes from the request body, so without a cap a
    # single POST asks for 518,918,400 codes -- about 62 GB of tuples -- and
    # the process dies. Free for the attacker, fatal for everyone else.
    response = client.post(
        "/game", json={"ruleset": {"length": 8, "alphabet": "0123456789ABCDEF"}}
    )
    assert response.status_code == 422
    assert response.json()["error"] == "invalid"
    assert "518,918,400" in response.json()["detail"]


def test_the_rulesets_the_app_offers_are_all_allowed(client):
    # The cap has to refuse the absurd without refusing the product. These are
    # every ruleset the benchmarks and the app actually use.
    for rules in (
        {"length": 4, "alphabet": "123456789"},
        {"length": 4, "alphabet": "0123456789"},
        {"length": 4, "alphabet": "0123456789", "allow_repeats": True},
        {"length": 5, "alphabet": "1234", "allow_repeats": True},
        {"length": 4, "alphabet": "0123456789ABCDEF"},
    ):
        response = client.post("/game", json={"ruleset": rules})
        assert response.status_code == 201, (rules, response.text)


def test_requests_are_rate_limited():
    ticks = [0.0]
    limiter = RateLimiter(per_minute=60, burst=3, clock=lambda: ticks[0])
    with TestClient(create_app(SessionStore(), limiter)) as limited:
        for _ in range(3):
            assert limited.get("/game/nope/state").status_code == 404
        response = limited.get("/game/nope/state")
        assert response.status_code == 429
        assert response.json()["error"] == "rate_limited"


def test_tokens_refill_over_time():
    ticks = [0.0]
    limiter = RateLimiter(per_minute=60, burst=2, clock=lambda: ticks[0])
    with TestClient(create_app(SessionStore(), limiter)) as limited:
        for _ in range(2):
            limited.get("/game/nope/state")
        assert limited.get("/game/nope/state").status_code == 429
        ticks[0] = 5.0  # 60/min is one per second
        assert limited.get("/game/nope/state").status_code == 404


def test_the_limiter_is_per_client():
    ticks = [0.0]
    limiter = RateLimiter(per_minute=60, burst=1, clock=lambda: ticks[0])
    assert limiter.allow("a")
    assert not limiter.allow("a")
    assert limiter.allow("b"), "one client's traffic must not exhaust another's"


def test_a_rate_limited_client_raises_its_own_exception():
    ticks = [0.0]
    limiter = RateLimiter(per_minute=60, burst=1, clock=lambda: ticks[0])
    with TestClient(create_app(SessionStore(), limiter)) as limited:
        RemoteGame.start(limited, ruleset=SMALL, seed=7)
        with pytest.raises(RateLimitedError):
            RemoteGame.start(limited, ruleset=SMALL, seed=7)
