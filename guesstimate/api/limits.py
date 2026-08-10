"""What a public endpoint refuses to do on request.

Two different protections. The rate limiter caps how *often* a client can ask;
the space cap caps how *expensive* a single ask may be. The second is the one
that matters more here, and it is not obvious until you look: the server
materialises the whole candidate space to start a game, and the ruleset comes
straight from the request body.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

#: Largest candidate space a request may ask the server to build. A game is
#: created by enumerating every code, so this is a memory limit wearing a
#: game-rules costume: length 8 over a hex alphabet is 518,918,400 codes, which
#: is roughly 62 GB of tuples and a dead process. 100,000 comfortably covers
#: every ruleset the app offers -- the 5040 standard variant, the 10,000-code
#: repeats mode, hex at length 4 -- and refuses the ones nobody asked for.
DEFAULT_MAX_SPACE = 100_000

#: Requests per minute per client, and how many may arrive at once. A game is
#: five or six guesses, so a human needs a handful of requests a minute and a
#: script does not need to be accommodated.
DEFAULT_PER_MINUTE = 120
DEFAULT_BURST = 30


@dataclass
class _Bucket:
    tokens: float
    updated: float = field(default=0.0)


class RateLimiter:
    """A token bucket per client.

    Hand-rolled rather than pulled in: it is thirty lines, the stdlib has
    everything it needs, and a dependency would have to be justified against a
    rule that says use the stdlib when it is under about that (CLAUDE.md rule
    6).

    In-memory and per-process, which matches the session store and has the same
    consequence: run two workers and each enforces its own limit. That is
    honest for a single-process deployment and would need replacing by
    something shared before scaling out -- noted here rather than discovered
    later.

    The clock is injected so tests can advance time without sleeping.
    """

    def __init__(
        self,
        per_minute: int = DEFAULT_PER_MINUTE,
        burst: int = DEFAULT_BURST,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.rate = per_minute / 60.0
        self.burst = float(burst)
        self._clock = time.monotonic if clock is None else clock
        self._buckets: dict[str, _Bucket] = {}

    def allow(self, key: str) -> bool:
        """Spend a token for `key`, or refuse."""
        now = self._clock()
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = _Bucket(tokens=self.burst, updated=now)
            self._buckets[key] = bucket

        elapsed = max(0.0, now - bucket.updated)
        bucket.tokens = min(self.burst, bucket.tokens + elapsed * self.rate)
        bucket.updated = now

        if bucket.tokens < 1.0:
            return False
        bucket.tokens -= 1.0
        return True

    def reset(self) -> None:
        """Forget every client. For tests."""
        self._buckets.clear()
