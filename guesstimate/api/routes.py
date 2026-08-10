"""HTTP routes. Thin wrappers over `guesstimate.game`, with no game logic.

Every handler does the same three things: parse at the boundary, call one
method on a `Game`, render the result. If a handler ever needs to know how a
mode works, the logic has gone in the wrong layer -- the offline build calls
the same objects with no HTTP anywhere near them.
"""

from __future__ import annotations

import random
from collections.abc import Awaitable, Callable

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from guesstimate.core import Feedback, format_code, parse_code
from guesstimate.game import (
    GameOverError,
    LocalCodebreakerGame,
    LocalRaceGame,
    LocalWatchGame,
    ObservedGame,
    ScoredGame,
    SolverBackedGame,
)
from guesstimate.solvers import SOLVERS, InconsistentFeedbackError

from .limits import DEFAULT_MAX_SPACE, RateLimiter
from .schemas import (
    CandidatesResponse,
    ErrorCode,
    FeedbackRequest,
    GameStateSchema,
    GuessRequest,
    NewGameRequest,
    SolverTurnResultSchema,
    TurnResultSchema,
)
from .sessions import Session, SessionStore


def _error(status: int, code: ErrorCode, detail: str) -> JSONResponse:
    """Refuse with a code the client can map to an exception."""
    return JSONResponse(status_code=status, content={"error": code, "detail": detail})


class _Refusal(HTTPException):
    """An HTTPException that carries an error code as well as a message."""

    def __init__(self, status: int, code: ErrorCode, detail: str) -> None:
        super().__init__(status, detail)
        self.code = code


def create_app(
    store: SessionStore | None = None,
    limiter: RateLimiter | None = None,
    max_space: int = DEFAULT_MAX_SPACE,
) -> FastAPI:
    """Build the application, optionally against supplied limits and storage."""
    app = FastAPI(
        title="Guesstimate",
        description="Bulls and Cows: play it, or watch a solver play it.",
        version="0.1.0",
    )
    app.state.store = store if store is not None else SessionStore()
    app.state.limiter = limiter if limiter is not None else RateLimiter()
    app.state.max_space = max_space

    @app.middleware("http")
    async def _rate_limit(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        client = request.client.host if request.client else "unknown"
        if not app.state.limiter.allow(client):
            return _error(429, "rate_limited", "too many requests; slow down and retry")
        return await call_next(request)

    def sessions() -> SessionStore:
        return app.state.store  # type: ignore[no-any-return]

    def require_session(
        game_id: str, store: SessionStore = Depends(sessions)
    ) -> Session:
        session = store.get(game_id)
        if session is None:
            raise _Refusal(
                404, "not_found", f"no game {game_id!r}; it may have expired"
            )
        return session

    @app.exception_handler(InconsistentFeedbackError)
    async def _inconsistent(
        request: Request, exc: InconsistentFeedbackError
    ) -> JSONResponse:
        # A human scoring by hand gets this wrong regularly, so it is a 409
        # rather than a 400: the request is well-formed, it just contradicts
        # the conversation so far. The game is untouched and still playable.
        return _error(409, "inconsistent_feedback", str(exc))

    @app.exception_handler(GameOverError)
    async def _finished(request: Request, exc: GameOverError) -> JSONResponse:
        return _error(409, "game_over", str(exc))

    @app.exception_handler(_Refusal)
    async def _refused(request: Request, exc: _Refusal) -> JSONResponse:
        return _error(exc.status_code, exc.code, str(exc.detail))

    @app.post("/game", response_model=GameStateSchema, status_code=201)
    def new_game(
        body: NewGameRequest, store: SessionStore = Depends(sessions)
    ) -> GameStateSchema:
        """Start a game."""
        try:
            ruleset = body.ruleset.to_domain()
        except ValueError as error:
            raise _Refusal(422, "invalid", str(error)) from error
        # The server enumerates the whole candidate space to start a game, and
        # the ruleset arrives in the request body. Without this, one POST
        # asking for length 8 over a hex alphabet is 518,918,400 codes and a
        # dead process -- a denial of service that costs the attacker nothing.
        if ruleset.space_size > app.state.max_space:
            raise _Refusal(
                422,
                "invalid",
                f"that ruleset has {ruleset.space_size:,} possible codes; this "
                f"server will not build more than {app.state.max_space:,}",
            )
        if body.solver not in SOLVERS:
            raise _Refusal(422, "invalid", f"unknown solver {body.solver!r}")

        rng = random.Random(body.seed)
        secret = None
        if body.secret is not None:
            try:
                secret = parse_code(body.secret, ruleset)
            except ValueError as error:
                raise _Refusal(422, "invalid", str(error)) from error

        game: ScoredGame | ObservedGame
        if body.mode == "codebreaker":
            game = LocalCodebreakerGame(ruleset, secret=secret, rng=rng)
        elif body.mode == "race":
            game = LocalRaceGame(
                ruleset, secret=secret, rng=rng, solver_name=body.solver
            )
        else:
            game = LocalWatchGame(ruleset, solver_name=body.solver, rng=rng)

        game_id = store.create(game, body.mode)
        return GameStateSchema.of(
            game_id, body.mode, game.state, len(game.candidate_indices())
        )

    @app.get("/game/{game_id}/state", response_model=GameStateSchema)
    def get_state(
        game_id: str, session: Session = Depends(require_session)
    ) -> GameStateSchema:
        """The board so far."""
        return GameStateSchema.of(
            game_id,
            session.mode,
            session.game.state,
            len(session.game.candidate_indices()),
        )

    @app.get("/game/{game_id}/candidates", response_model=CandidatesResponse)
    def get_candidates(
        game_id: str, session: Session = Depends(require_session)
    ) -> CandidatesResponse:
        """Surviving candidates as grid positions."""
        indices = session.game.candidate_indices()
        return CandidatesResponse(
            total=session.game.state.ruleset.space_size, indices=list(indices)
        )

    @app.post("/game/{game_id}/guess", response_model=TurnResultSchema)
    def post_guess(
        game_id: str,
        body: GuessRequest,
        session: Session = Depends(require_session),
    ) -> TurnResultSchema:
        """Play a code. Only modes that can score one accept this."""
        game = session.game
        if not isinstance(game, ScoredGame):
            raise _Refusal(
                409,
                "wrong_mode",
                f"{session.mode} mode cannot score a guess; the secret is not "
                f"the server's to check",
            )
        try:
            code = parse_code(body.guess, game.state.ruleset)
        except ValueError as error:
            raise _Refusal(422, "invalid", str(error)) from error
        return TurnResultSchema.of(game.guess(code))

    @app.get("/game/{game_id}/solver-guess")
    def get_solver_guess(
        game_id: str, session: Session = Depends(require_session)
    ) -> dict[str, str]:
        """The solver's opening move.

        Only needed once per game. Every later move arrives with the answer to
        the previous one, since watch mode strictly alternates and a separate
        round trip per turn would buy nothing.
        """
        game = session.game
        if not isinstance(game, SolverBackedGame):
            raise _Refusal(409, "wrong_mode", f"{session.mode} mode has no solver")
        return {"guess": format_code(game.solver_guess())}

    @app.post("/game/{game_id}/feedback", response_model=SolverTurnResultSchema)
    def post_feedback(
        game_id: str,
        body: FeedbackRequest,
        session: Session = Depends(require_session),
    ) -> SolverTurnResultSchema:
        """Answer the solver, and get its next move back."""
        game = session.game
        if not isinstance(game, ObservedGame):
            raise _Refusal(
                409,
                "wrong_mode",
                f"{session.mode} mode does not take feedback from the player",
            )
        try:
            feedback = Feedback.parse(body.feedback)
        except ValueError as error:
            raise _Refusal(422, "invalid", str(error)) from error
        return SolverTurnResultSchema.of_solver(game.submit_feedback(feedback))

    return app


app = create_app()
