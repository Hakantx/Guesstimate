"""A `Game` that lives on the other end of an HTTP connection.

The second implementation of the protocol, and the reason it exists at all: a
protocol with one implementation quietly describes that implementation rather
than the idea behind it, and the drift would surface in a browser rather than
in pytest. Phase 7's TypeScript client will be the third, and this is what
keeps the shape honest until then.

It is not scaffolding either. Phase 10's LLM harness drives games through the
same `Game` interface as every other player, and against a deployed server that
means through this.
"""

from __future__ import annotations

from typing import Any

import httpx

from guesstimate.core import Code, Feedback, Ruleset, format_code, parse_code
from guesstimate.game import (
    GameOverError,
    GameState,
    SecretHidden,
    SecretNever,
    SecretRevealed,
    SolverTurnResult,
    Turn,
    TurnResult,
)
from guesstimate.solvers import InconsistentFeedbackError


class RemoteGame:
    """Plays through the API. Satisfies `ScoredGame` and `ObservedGame`.

    Holds a game id and a client, which are exactly the two things CLAUDE.md
    rule 10 keeps out of the shared layer. Nothing above this class needs to
    know either exists.
    """

    def __init__(self, client: httpx.Client, game_id: str, mode: str) -> None:
        self.client = client
        self.game_id = game_id
        self.mode = mode

    @classmethod
    def start(
        cls,
        client: httpx.Client,
        mode: str = "codebreaker",
        ruleset: Ruleset | None = None,
        solver: str = "entropy",
        seed: int | None = None,
        secret: Code | None = None,
    ) -> RemoteGame:
        """Create a game on the server and return a handle to it."""
        rules = Ruleset() if ruleset is None else ruleset
        payload: dict[str, Any] = {
            "mode": mode,
            "solver": solver,
            "seed": seed,
            "ruleset": {
                "length": rules.length,
                "alphabet": rules.alphabet,
                "allow_repeats": rules.allow_repeats,
            },
        }
        if secret is not None:
            payload["secret"] = format_code(secret)
        response = client.post("/game", json=payload)
        _raise_for(response)
        return cls(client, response.json()["id"], mode)

    def _get(self, path: str) -> dict[str, Any]:
        response = self.client.get(f"/game/{self.game_id}{path}")
        _raise_for(response)
        return dict(response.json())

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        response = self.client.post(f"/game/{self.game_id}{path}", json=body)
        _raise_for(response)
        return dict(response.json())

    @property
    def state(self) -> GameState:
        """Fetch and rebuild the board."""
        return _state_from(self._get("/state"))

    def candidate_indices(self) -> tuple[int, ...]:
        """Surviving candidates as grid positions."""
        return tuple(self._get("/candidates")["indices"])

    def guess(self, code: Code) -> TurnResult:
        """Play a code."""
        body = self._post("/guess", {"guess": format_code(code)})
        return TurnResult(
            feedback=Feedback.parse(body["feedback"]),
            finished=body["finished"],
            surviving=body["surviving"],
        )

    def solver_guess(self) -> Code:
        """The solver's opening move."""
        body = self._get("/solver-guess")
        return parse_code(body["guess"], self.state.ruleset)

    def submit_feedback(self, feedback: Feedback) -> SolverTurnResult:
        """Answer the solver, and get its next move back in the same reply."""
        body = self._post("/feedback", {"feedback": str(feedback)})
        ruleset = self.state.ruleset
        return SolverTurnResult(
            feedback=Feedback.parse(body["feedback"]),
            finished=body["finished"],
            surviving=body["surviving"],
            next_guess=(
                None
                if body["next_guess"] is None
                else parse_code(body["next_guess"], ruleset)
            ),
        )


class RateLimitedError(RuntimeError):
    """The server is asking for fewer requests."""


class ModeNotSupportedError(RuntimeError):
    """The operation is not one this game's mode offers.

    A statically typed caller cannot reach this -- the protocol split means a
    codebreaker game has no `submit_feedback` to call. It exists because HTTP
    has no such protection, so a hand-rolled client or a browser can ask.
    """


#: One exception per error code, and no inference. The server used to send a
#: boolean and the client guessed which exception it meant; that worked only
#: while there were exactly two failures to tell apart, and quietly encoded the
#: assumption that there always would be.
_ERRORS: dict[str, type[Exception]] = {
    "inconsistent_feedback": InconsistentFeedbackError,
    "game_over": GameOverError,
    "wrong_mode": ModeNotSupportedError,
    "not_found": LookupError,
    "invalid": ValueError,
    "rate_limited": RateLimitedError,
}


def _raise_for(response: httpx.Response) -> None:
    """Turn a transport-level failure back into the domain exception it was.

    A caller written against `Game` catches `InconsistentFeedbackError`. It
    should not have to also catch an HTTP status to handle the same mistake
    made over a wire -- that difference is what makes two implementations of
    one protocol behave differently in a way mypy cannot see.
    """
    if response.is_success:
        return

    detail = response.text
    code = None
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        detail = str(body.get("detail", detail))
        raw = body.get("error")
        code = raw if isinstance(raw, str) else None

    if code is not None:
        exception = _ERRORS.get(code)
        if exception is not None:
            raise exception(detail)
        # An unknown code from a newer server: better a loud unknown than a
        # wrong guess at which exception was meant.
        raise RuntimeError(f"unrecognised error code {code!r}: {detail}")
    response.raise_for_status()


def _state_from(body: dict[str, Any]) -> GameState:
    rules = body["ruleset"]
    ruleset = Ruleset(
        length=rules["length"],
        alphabet=rules["alphabet"],
        allow_repeats=rules["allow_repeats"],
    )
    secret_body = body["secret"]
    kind = secret_body["kind"]
    if kind == "revealed":
        secret: SecretHidden | SecretRevealed | SecretNever = SecretRevealed(
            parse_code(secret_body["code"], ruleset)
        )
    elif kind == "never":
        secret = SecretNever()
    else:
        secret = SecretHidden()

    return GameState(
        ruleset=ruleset,
        turns=tuple(
            Turn(
                guess=parse_code(turn["guess"], ruleset),
                feedback=Feedback.parse(turn["feedback"]),
            )
            for turn in body["turns"]
        ),
        finished=body["finished"],
        won=body["won"],
        secret=secret,
    )
