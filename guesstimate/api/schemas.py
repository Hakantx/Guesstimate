"""Wire formats.

Deliberately separate from the dataclasses in `guesstimate.game`. The domain
types are what the offline build uses and they must stay free of anything
web-shaped (CLAUDE.md rule 10); these are what crosses the wire. Converting
between them is a few lines and keeps the coupling one-directional.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from guesstimate.core import Ruleset, format_code
from guesstimate.game import (
    GameState,
    SecretNever,
    SecretRevealed,
    SolverTurnResult,
    TurnResult,
)


class RulesetSchema(BaseModel):
    """The rules a game is played under."""

    length: int = 4
    alphabet: str = "123456789"
    allow_repeats: bool = False

    def to_domain(self) -> Ruleset:
        """Build the engine's ruleset, raising ValueError if impossible."""
        return Ruleset(
            length=self.length,
            alphabet=self.alphabet,
            allow_repeats=self.allow_repeats,
        )

    @classmethod
    def of(cls, ruleset: Ruleset) -> RulesetSchema:
        """Render an engine ruleset."""
        return cls(
            length=ruleset.length,
            alphabet=ruleset.alphabet,
            allow_repeats=ruleset.allow_repeats,
        )


class NewGameRequest(BaseModel):
    """What to start."""

    mode: Literal["codebreaker", "watch", "race", "evil"] = "codebreaker"
    ruleset: RulesetSchema = Field(default_factory=RulesetSchema)
    solver: str = "entropy"
    seed: int | None = None
    secret: str | None = Field(
        default=None,
        description=(
            "Fix the code, for demos and reproducible tests. Ignored by watch "
            "mode, which has no secret."
        ),
    )


class TurnSchema(BaseModel):
    """One completed exchange."""

    guess: str
    feedback: str


class SecretSchema(BaseModel):
    """Three states, discriminated on the wire as they are in the domain.

    `kind` is always present, so a client can tell a withheld secret from one
    that never existed without inspecting whether `code` happens to be null.
    """

    kind: Literal["hidden", "revealed", "never"]
    code: str | None = None


class GameStateSchema(BaseModel):
    """Everything a client may know right now."""

    id: str
    mode: str
    ruleset: RulesetSchema
    turns: list[TurnSchema]
    finished: bool
    won: bool
    secret: SecretSchema
    surviving: int
    space_size: int = Field(
        description=(
            "How many codes the ruleset allows in total. Served rather than "
            "left for the client to derive: it is a falling factorial or a "
            "power depending on `allow_repeats`, and a second implementation "
            "of that in another language is a divergence waiting to happen "
            "somewhere no Python test can reach."
        )
    )
    outcomes: list[str] = Field(
        description=(
            "Every answer this ruleset can actually produce, as `+B-C`. Sent "
            "because it is not derivable from the code length: which outcomes "
            "are reachable depends on the alphabet too. Four positions over "
            "two symbols with repeats reaches nine of the fourteen a "
            "bulls-plus-cows triangle would suggest, so a client computing the "
            "set itself would offer answers that can never be correct."
        ),
    )

    @classmethod
    def of(
        cls,
        game_id: str,
        mode: str,
        state: GameState,
        surviving: int,
        outcomes: tuple[str, ...] = (),
    ) -> GameStateSchema:
        """Render a domain state for the wire."""
        if isinstance(state.secret, SecretRevealed):
            secret = SecretSchema(kind="revealed", code=format_code(state.secret.code))
        elif isinstance(state.secret, SecretNever):
            secret = SecretSchema(kind="never")
        else:
            secret = SecretSchema(kind="hidden")

        return cls(
            id=game_id,
            mode=mode,
            ruleset=RulesetSchema.of(state.ruleset),
            turns=[
                TurnSchema(guess=format_code(t.guess), feedback=str(t.feedback))
                for t in state.turns
            ],
            finished=state.finished,
            won=state.won,
            secret=secret,
            surviving=surviving,
            space_size=state.ruleset.space_size,
            outcomes=list(outcomes),
        )


class GuessRequest(BaseModel):
    """A code to play."""

    guess: str


class FeedbackRequest(BaseModel):
    """An answer to the solver's last guess, as `+B-C`."""

    feedback: str


class TurnResultSchema(BaseModel):
    """What one turn produced."""

    feedback: str
    finished: bool
    surviving: int

    @classmethod
    def of(cls, result: TurnResult) -> TurnResultSchema:
        """Render a domain result."""
        return cls(
            feedback=str(result.feedback),
            finished=result.finished,
            surviving=result.surviving,
        )


class SolverTurnResultSchema(TurnResultSchema):
    """A turn in a mode where the solver moves next.

    `next_guess` is null exactly when `finished` is true, matching the domain
    invariant, so watch mode needs one round trip per turn rather than two.
    """

    next_guess: str | None = None

    @classmethod
    def of_solver(cls, result: SolverTurnResult) -> SolverTurnResultSchema:
        """Render a domain result that carries the solver's next move."""
        return cls(
            feedback=str(result.feedback),
            finished=result.finished,
            surviving=result.surviving,
            next_guess=(
                None if result.next_guess is None else format_code(result.next_guess)
            ),
        )


#: Every failure the API reports carries one of these, and each maps to exactly
#: one exception on the client. A boolean flag was the first design and it only
#: worked while there were two cases: the client had to infer *which* exception
#: from a flag that answered a different question, and a third failure would
#: have had nowhere to go. A code is one-to-one and extends by adding a member.
ErrorCode = Literal[
    "inconsistent_feedback",
    "game_over",
    "wrong_mode",
    "not_found",
    "invalid",
    "rate_limited",
]


class ErrorResponse(BaseModel):
    """A refusal, with a machine-readable reason."""

    error: ErrorCode
    detail: str


class MoveReviewSchema(BaseModel):
    """One graded move."""

    turn: int
    guess: str
    feedback: str
    survivors_before: int
    survivors_after: int
    eliminated: int = Field(
        description=(
            "How many codes this guess actually removed. Reported, never "
            "ranked on: the realized figure depends on which block the answer "
            "landed in, which is luck. A lopsided guess can remove more on a "
            "lucky answer while being much the worse guess."
        )
    )
    expected_remaining: float = Field(
        description=(
            "Codes still standing after this guess, in expectation, with the "
            "winning answer counted as none remaining. Lower is better."
        )
    )
    bits_gained: float
    best_candidate_remaining: float
    best_any_remaining: float
    best_candidate: str | None
    best_any: str | None
    probe_advantage: float = Field(
        description=(
            "What the best non-candidate probe would have bought over the best "
            "guess that could itself win. Explanatory, not graded on."
        )
    )
    probe_matters: bool = Field(
        description=(
            "Whether the probe was better by enough to be worth showing. False "
            "on most turns, when the best guess overall is simply the best "
            "candidate and the two numbers are identical."
        )
    )
    loss: float
    grade: str


class AnalysisResponse(BaseModel):
    """A finished game, move by move."""

    moves: list[MoveReviewSchema]
    total_loss: float
    mean_loss: float


class RaceTurnSchema(BaseModel):
    """One turn by the solver in a race, scored against the shared secret."""

    guess: str
    feedback: str
    finished: bool
    surviving: int


class CandidatesResponse(BaseModel):
    """Surviving candidates, as positions in `all_candidates(ruleset)`.

    Indices, not codes: the ordering is the grid ordering in DESIGN.md, so the
    visualisation consumes these directly instead of rebuilding a
    code-to-position table the server already has.
    """

    total: int
    indices: list[int]
