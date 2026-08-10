"""What a game in progress is, independent of where it is running.

CLAUDE.md rule 10: the same game logic has to sit behind a local in-process
solver with no network at all, because offline play is what makes the mobile
app more than a website in a shell. So the game is an interface with two
implementations rather than a set of HTTP routes with logic in them. Nothing
here knows about sessions, round trips, or a server clock; those are
`RemoteGame` details.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from guesstimate.core import Code, Feedback, Ruleset


@dataclass(frozen=True)
class Turn:
    """One completed exchange: a code, and what it drew."""

    guess: Code
    feedback: Feedback


@dataclass(frozen=True)
class SecretHidden:
    """There is a secret and the game is not showing it yet."""


@dataclass(frozen=True)
class SecretRevealed:
    """The game is over and this was the code."""

    code: Code


@dataclass(frozen=True)
class SecretNever:
    """There was never a code at all.

    Evil mode's whole premise: the codemaker answers adversarially, choosing
    whichever reply keeps the most candidates alive, and commits to nothing
    until it is cornered. A reveal screen has to be able to say "there was no
    code" rather than showing a blank where one would go.

    If the game ran to the end, exactly one candidate remains, and
    `candidate_indices` is where to find it. It is what the player forced, not
    what anyone chose, which is why it is not carried here as a `code`.
    """


Secret = SecretHidden | SecretRevealed | SecretNever
"""Three states, discriminated.

`Code | None` was the first design and it conflated two different things: a
secret being withheld and a secret never having existed. Those need different
words on a reveal screen, and a mode whose entire point is the second one would
have been indistinguishable from an unfinished game.
"""


@dataclass(frozen=True)
class GameState:
    """Everything a client may know about a game right now."""

    ruleset: Ruleset
    turns: tuple[Turn, ...]
    finished: bool
    won: bool
    secret: Secret


@dataclass(frozen=True)
class TurnResult:
    """What one turn produced."""

    feedback: Feedback
    finished: bool
    surviving: int


@dataclass(frozen=True)
class SolverTurnResult(TurnResult):
    """A turn in a mode where the solver moves next.

    Watch mode strictly alternates: the solver guesses, the player answers, the
    solver guesses again. Returning the next move with the answer collapses
    what would otherwise be two round trips per turn into one, and it keeps
    *which games can be asked for a solver move* in the type system rather than
    in a comment -- only `ObservedGame.submit_feedback` returns this.

    Attributes:
        next_guess: What the solver will play now. `None` exactly when the game
            has finished, so `next_guess is None` and `finished` always agree.
    """

    next_guess: Code | None


class GameOverError(RuntimeError):
    """A move was played on a finished game."""


@runtime_checkable
class Game(Protocol):
    """Every mode, and the least that can be said about one.

    Runtime-checkable, unlike the `Solver` protocol, and for a different job.
    There, `isinstance` was rejected because it only compares method *names*
    and would have passed a solver whose `update` took the wrong arguments --
    conformance needs real signature checks. Here the question a route asks is
    exactly "does this game have a `guess` method", which is precisely what
    name checking answers. Dispatching on capability is what these are for.

    Deliberately small. `guess` is *not* here, because whether a game can score
    a guess at all is a per-mode capability rather than something every game
    has -- see `ScoredGame`.
    """

    @property
    def state(self) -> GameState:
        """The board so far, and whether it is over."""
        ...

    def candidate_indices(self) -> tuple[int, ...]:
        """Codes still possible, as positions in `all_candidates(ruleset)`.

        Indices rather than codes: the ordering is the grid ordering in
        DESIGN.md, and handing out positions keeps the code-to-position mapping
        in one place instead of making every consumer rebuild it.
        """
        ...


@runtime_checkable
class ScoredGame(Game, Protocol):
    """A game that can score a guess itself.

    True when the game knows the answer -- either because it holds a secret
    (codebreaker, race) or because it is entitled to invent one consistent with
    everything it has already said (evil).
    """

    def guess(self, code: Code) -> TurnResult:
        """Play a code and be told how close it was.

        Raises:
            GameOverError: If the game has already finished.
            ValueError: If the code is not legal under the ruleset.
        """
        ...


@runtime_checkable
class SolverBackedGame(Game, Protocol):
    """A game with a solver that will propose moves."""

    def solver_guess(self) -> Code:
        """What the solver would play next. Does not commit to it."""
        ...


@runtime_checkable
class ObservedGame(SolverBackedGame, Protocol):
    """The solver guesses and the *human* scores -- watch mode.

    This is why `guess` cannot live on `Game`. Here the secret is in the
    player's head and nowhere else, so the game has no way to score a code it
    is handed; the only move available is answering the solver. A protocol that
    demanded `guess` of every mode would force this one to implement a method
    that can only raise.
    """

    def submit_feedback(self, feedback: Feedback) -> SolverTurnResult:
        """Answer the solver's last guess, and be told the next one.

        Raises:
            GameOverError: If the game has already finished.
            InconsistentFeedbackError: If no candidate survives the answer,
                which means an earlier answer contradicts this one. The CLI
                already treats this as recoverable and so should any caller:
                the turn is dropped and the solver is left as it was.
        """
        ...


@runtime_checkable
class RacedGame(ScoredGame, SolverBackedGame, Protocol):
    """Player and solver race on the same secret. Both capabilities, no extras."""
