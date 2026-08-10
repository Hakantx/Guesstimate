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

from guesstimate.core import Ruleset

#: Largest candidate space a request may ask the server to build. A game is
#: created by enumerating every code, so this is a memory limit wearing a
#: game-rules costume: length 8 over a hex alphabet is 518,918,400 codes, which
#: is roughly 62 GB of tuples and a dead process. 100,000 comfortably covers
#: every ruleset the app offers -- the 5040 standard variant, the 10,000-code
#: repeats mode, hex at length 4 -- and refuses the ones nobody asked for.
DEFAULT_MAX_SPACE = 100_000

#: How long one request may spend computing a first turn. A game is created
#: synchronously, so this is how long a stranger may make a worker wait.
DEFAULT_TURN_BUDGET_SECONDS = 1.0

#: Requests per minute per client, and how many may arrive at once. A game is
#: five or six guesses, so a human needs a handful of requests a minute and a
#: script does not need to be accommodated.
DEFAULT_PER_MINUTE = 120
DEFAULT_BURST = 30


def _relabelling_classes(ruleset: Ruleset) -> int:
    """How many symbol patterns a code of this shape can have.

    With no repeats every code is the same all-distinct pattern, so there is
    one. With repeats it is the number of ways to partition the positions into
    at most `len(alphabet)` groups -- a sum of Stirling numbers of the second
    kind. Counted rather than enumerated, because this is used to *estimate*
    work before agreeing to do it.
    """
    if not ruleset.allow_repeats:
        return 1

    length = ruleset.length
    groups = min(length, len(ruleset.alphabet))
    # stirling[k] holds S(n, k) as n climbs.
    stirling = [0] * (length + 1)
    stirling[0] = 1
    for _ in range(length):
        stirling = [
            (stirling[k - 1] if k else 0) + k * stirling[k] for k in range(length + 1)
        ]
    return sum(stirling[1 : groups + 1])


#: Reachable answers, memoised per ruleset. Bounded so that a caller asking for
#: thousands of distinct rulesets cannot grow it without limit; the whole cache
#: is dropped rather than evicted one entry at a time, because the working set
#: is a handful of rulesets and an LRU would be machinery for nothing.
_MAX_CACHED_OUTCOMES = 256
_OUTCOMES: dict[Ruleset, tuple[str, ...]] = {}


def outcomes_for(ruleset: Ruleset) -> tuple[str, ...]:
    """Every answer this ruleset can produce, as `+B-C`, computed once.

    Memoised for the same reason the feedback matrix is: it is a pure function
    of the rules, it costs a pass over the candidate space, and the app serves
    a small number of rulesets over and over.
    """
    cached = _OUTCOMES.get(ruleset)
    if cached is not None:
        return cached

    from guesstimate.core import feedback_space

    computed = tuple(str(outcome) for outcome in feedback_space(ruleset))
    if len(_OUTCOMES) >= _MAX_CACHED_OUTCOMES:
        _OUTCOMES.clear()
    _OUTCOMES[ruleset] = computed
    return computed


def outcome_scan_seconds(ruleset: Ruleset) -> float:
    """Estimated seconds to enumerate a ruleset's reachable answers.

    Zero once they are memoised. Enumerating is one scoring per candidate per
    relabelling class, which is trivial for the classic game and about a second
    for ten thousand codes with repeats -- affordable once, not per request,
    which is exactly what the memo is for.
    """
    if ruleset in _OUTCOMES:
        return 0.0

    from guesstimate.data import scoring_rate

    return _relabelling_classes(ruleset) * ruleset.space_size * scoring_rate()


def first_turn_seconds(ruleset: Ruleset, solver_name: str | None) -> float:
    """Estimated seconds to compute the opening move for this configuration.

    The space cap alone is not enough, and the reason is that it bounds memory
    while the expensive thing is CPU. Starting a game allocates the candidate
    list once; *choosing a guess* compares every candidate guess against every
    surviving candidate, which is quadratic and happens per turn.

    Three cases, and they differ by orders of magnitude:

    - **No solver at all.** Codebreaker mode scores the player's guess against
      one secret and filters, which is linear. A large space costs memory and
      nothing else.
    - **`RandomSolver`.** Picks uniformly from the survivors. Also linear.
    - **A scoring solver.** Quadratic, and whether it is bearable depends
      entirely on which partitioner serves it -- about three hundred times
      between them -- plus the one-off matrix build if none is cached.

    One number for all four would therefore be wrong in both directions at
    once: low enough to protect against entropy is far below what random can
    comfortably take.
    """
    if solver_name is None:
        return 0.0

    from guesstimate.data import estimate, matrix_path, matrix_scan_rate, scoring_rate
    from guesstimate.solvers import SOLVERS, PartitionSolver

    solver = SOLVERS.get(solver_name)
    if solver is None or not issubclass(solver, PartitionSolver):
        return 0.0  # linear per turn; the space cap already covers it

    pairs = ruleset.space_size**2
    costs = estimate(ruleset)
    if not costs.affordable:
        return pairs * scoring_rate()

    # A matrix that is already on disk costs nothing to load. One that is not
    # gets built inside this request, so the build is part of what the caller
    # is asking a worker to do -- and it is the larger half by far.
    build = 0.0 if matrix_path(ruleset).exists() else costs.build_seconds
    return build + pairs * matrix_scan_rate()


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
