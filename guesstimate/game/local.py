"""Games played entirely in this process. No network, no session, no clock."""

from __future__ import annotations

import random

from guesstimate.core import Code, Feedback, Ruleset, all_candidates, score
from guesstimate.solvers import SOLVERS, BaseSolver, Partitioner

from .protocol import (
    GameOverError,
    GameState,
    SecretHidden,
    SecretRevealed,
    SolverTurnResult,
    Turn,
    TurnResult,
)


class _Base:
    """Turn bookkeeping every local game shares."""

    def __init__(self, ruleset: Ruleset) -> None:
        self.ruleset = ruleset
        self._turns: list[Turn] = []
        self._finished = False
        self._won = False

    def _require_open(self) -> None:
        if self._finished:
            raise GameOverError("this game is already over")

    def _record(self, guess: Code, feedback: Feedback) -> None:
        self._turns.append(Turn(guess=guess, feedback=feedback))
        if feedback.is_win(self.ruleset.length):
            self._finished = True
            self._won = True


class LocalCodebreakerGame(_Base):
    """The player guesses, the game scores. Satisfies `ScoredGame`.

    Holds the secret in memory and does not put it in `state` until the game is
    over. That is the same guarantee the server makes, expressed in the same
    place, so the offline build cannot accidentally be laxer than the hosted
    one.
    """

    def __init__(
        self,
        ruleset: Ruleset,
        secret: Code | None = None,
        rng: random.Random | None = None,
    ) -> None:
        super().__init__(ruleset)
        source = random.Random() if rng is None else rng
        self._secret = (
            source.choice(all_candidates(ruleset)) if secret is None else secret
        )
        self._survivors = all_candidates(ruleset)

    @property
    def state(self) -> GameState:
        """The board, with the secret withheld until the end."""
        return GameState(
            ruleset=self.ruleset,
            turns=tuple(self._turns),
            finished=self._finished,
            won=self._won,
            secret=SecretRevealed(self._secret) if self._finished else SecretHidden(),
        )

    def candidate_indices(self) -> tuple[int, ...]:
        """Codes consistent with every answer given so far."""
        space = all_candidates(self.ruleset)
        positions = {code: index for index, code in enumerate(space)}
        return tuple(positions[code] for code in self._survivors)

    def guess(self, code: Code) -> TurnResult:
        """Score a code against the secret."""
        self._require_open()
        feedback = score(self._secret, code)
        self._survivors = [
            candidate
            for candidate in self._survivors
            if score(candidate, code) == feedback
        ]
        self._record(code, feedback)
        return TurnResult(
            feedback=feedback,
            finished=self._finished,
            surviving=len(self._survivors),
        )


class LocalWatchGame(_Base):
    """The solver guesses, the player scores. Satisfies `ObservedGame`.

    There is no secret anywhere in this object -- it is in the player's head,
    which is exactly why `guess` is not part of this mode's interface.
    """

    def __init__(
        self,
        ruleset: Ruleset,
        solver_name: str = "entropy",
        rng: random.Random | None = None,
        partitioner: Partitioner | None = None,
        restrict_to_candidates: bool = True,
    ) -> None:
        super().__init__(ruleset)
        self._solver: BaseSolver = SOLVERS[solver_name](
            ruleset,
            rng=rng,
            partitioner=partitioner,
            restrict_to_candidates=restrict_to_candidates,
        )
        self._pending: Code | None = None

    @property
    def state(self) -> GameState:
        """The board. The secret was never here to reveal."""
        return GameState(
            ruleset=self.ruleset,
            turns=tuple(self._turns),
            finished=self._finished,
            won=self._won,
            secret=SecretRevealed(self._turns[-1].guess)
            if self._won
            else SecretHidden(),
        )

    def candidate_indices(self) -> tuple[int, ...]:
        """Whatever the solver still considers possible."""
        return self._solver.candidate_indices

    def solver_guess(self) -> Code:
        """The solver's next move. Asking twice gives the same answer."""
        self._require_open()
        if self._pending is None:
            self._pending = self._solver.guess()
        return self._pending

    def submit_feedback(self, feedback: Feedback) -> SolverTurnResult:
        """Answer the pending guess, and get the solver's next move with it.

        `InconsistentFeedbackError` propagates untouched: the solver refuses the
        answer and stays exactly as it was, so the caller can apologise and ask
        again rather than restart.
        """
        self._require_open()
        guess = self.solver_guess()
        # Always narrow, including on a claimed win. A player who says "+3-0"
        # to a guess that cannot be the secret is contradicting an earlier
        # answer, and skipping the update on wins would wave that through as a
        # victory -- the one mistake in this mode nobody would notice.
        self._solver.update(guess, feedback)
        self._record(guess, feedback)
        self._pending = None
        return SolverTurnResult(
            feedback=feedback,
            finished=self._finished,
            surviving=len(self._solver.candidates),
            next_guess=None if self._finished else self.solver_guess(),
        )


class LocalRaceGame(LocalCodebreakerGame):
    """Player and solver on the same secret. Satisfies `RacedGame`.

    The solver's moves are scored by the game like anyone else's, so this is a
    codebreaker game that also happens to hold an opinion about what to play.
    """

    def __init__(
        self,
        ruleset: Ruleset,
        secret: Code | None = None,
        rng: random.Random | None = None,
        solver_name: str = "entropy",
        partitioner: Partitioner | None = None,
    ) -> None:
        super().__init__(ruleset, secret=secret, rng=rng)
        self._solver: BaseSolver = SOLVERS[solver_name](
            ruleset, rng=rng, partitioner=partitioner
        )
        self._solver_turns: list[Turn] = []

    def solver_guess(self) -> Code:
        """What the solver would play against the same secret."""
        self._require_open()
        return self._solver.guess()

    def play_solver_turn(self) -> TurnResult:
        """Let the solver take its turn, scored against the same secret."""
        self._require_open()
        guess = self._solver.guess()
        feedback = score(self._secret, guess)
        self._solver_turns.append(Turn(guess=guess, feedback=feedback))
        if not feedback.is_win(self.ruleset.length):
            self._solver.update(guess, feedback)
        return TurnResult(
            feedback=feedback,
            finished=feedback.is_win(self.ruleset.length),
            surviving=len(self._solver.candidates),
        )

    @property
    def solver_turns(self) -> tuple[Turn, ...]:
        """The solver's board, kept separate from the player's."""
        return tuple(self._solver_turns)
