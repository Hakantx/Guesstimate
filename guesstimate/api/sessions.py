"""Where games live between requests.

Everything in this module is a Phase 6 detail. Session ids, expiry, and a
wall clock are exactly what CLAUDE.md rule 10 says must not leak into the
shared game layer, so they are all here and none of them are in
`guesstimate.game`.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field

from guesstimate.game import Game

#: How long an idle game survives. Long enough to think, short enough that a
#: process serving a public URL does not accumulate abandoned games forever.
DEFAULT_TTL_SECONDS = 60 * 60


@dataclass
class Session:
    """One game, plus the bookkeeping the domain deliberately knows nothing about."""

    game: Game
    mode: str
    created: float
    touched: float = field(default=0.0)
    #: Reachable answers for this ruleset, computed once at creation. Enumerating
    #: them costs a pass over the candidate space, which is affordable once per
    #: game and wasteful on every state request.
    outcomes: tuple[str, ...] = ()


class SessionStore:
    """In-memory games, keyed by id, expiring on idle.

    In memory on purpose: a database is on the explicit skip list in
    `ROADMAP.md`, and the daily challenge plus LocalStorage stats get most of
    the engagement without the operational cost. The consequence is that a
    restart drops games in progress, which for a puzzle that lasts five guesses
    is an acceptable trade rather than an oversight.

    The clock is injected so tests can expire a game without sleeping.
    """

    def __init__(
        self,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        clock: object | None = None,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self._clock = time.monotonic if clock is None else clock
        self._sessions: dict[str, Session] = {}

    def _now(self) -> float:
        return float(self._clock())  # type: ignore[operator]

    def create(self, game: Game, mode: str, outcomes: tuple[str, ...] = ()) -> str:
        """Store a game and return its id.

        The id is from `secrets`, not `random`: it is the only thing standing
        between one player's game and another's, so it wants to be unguessable
        rather than merely unique.
        """
        self.sweep()
        game_id = secrets.token_urlsafe(12)
        now = self._now()
        self._sessions[game_id] = Session(
            game=game, mode=mode, created=now, touched=now, outcomes=outcomes
        )
        return game_id

    def get(self, game_id: str) -> Session | None:
        """Fetch a game and mark it as still wanted."""
        session = self._sessions.get(game_id)
        if session is None:
            return None
        if self._now() - session.touched > self.ttl_seconds:
            del self._sessions[game_id]
            return None
        session.touched = self._now()
        return session

    def sweep(self) -> int:
        """Drop everything idle past the TTL. Returns how many went."""
        now = self._now()
        stale = [
            key
            for key, session in self._sessions.items()
            if now - session.touched > self.ttl_seconds
        ]
        for key in stale:
            del self._sessions[key]
        return len(stale)

    def __len__(self) -> int:
        """How many games are being held."""
        return len(self._sessions)
