"""The game, as an interface with local implementations.

CLAUDE.md rule 10 in code form. A game is defined by what it can do, not by how
it is hosted: the same objects back the CLI, the offline mobile build, and the
Phase 6 HTTP routes, and nothing in here mentions a session id or a round trip.

The protocols split on two capabilities rather than one, because the modes do:

    Game                state + candidate_indices        every mode
    ScoredGame          + guess(code)                    codebreaker, race, evil
    SolverBackedGame    + solver_guess()                 watch, race
    ObservedGame        + submit_feedback(fb)            watch
    RacedGame           both of the above                race

Watch mode is why `guess` is not on the base: there the secret is in the
player's head, so the game cannot score a code it is handed.
"""

from .local import LocalCodebreakerGame, LocalRaceGame, LocalWatchGame
from .protocol import (
    Game,
    GameOverError,
    GameState,
    ObservedGame,
    RacedGame,
    ScoredGame,
    Secret,
    SecretHidden,
    SecretNever,
    SecretRevealed,
    SolverBackedGame,
    SolverTurnResult,
    Turn,
    TurnResult,
)

__all__ = [
    "Game",
    "GameOverError",
    "GameState",
    "LocalCodebreakerGame",
    "LocalRaceGame",
    "LocalWatchGame",
    "ObservedGame",
    "RacedGame",
    "ScoredGame",
    "Secret",
    "SecretHidden",
    "SecretNever",
    "SecretRevealed",
    "SolverBackedGame",
    "SolverTurnResult",
    "Turn",
    "TurnResult",
]
