"""Reusing analysis, because it does not depend on the secret.

A review is a pure function of the transcript. The same opening from the same
ruleset produces the same numbers for every player who makes it, and asking
twice for a finished game's review should cost nothing the second time.

That matters most where it is least obvious. In Phase 9 thousands of people
play the same daily secret, a large fraction open with the same handful of
codes, and every one of those openings is the same search over the same 3,024
candidates. Keying on a session would compute it once per player.
"""

from __future__ import annotations

from collections.abc import Sequence

from guesstimate.core import Code, Feedback, Ruleset, format_code

TranscriptKey = tuple[int, str, bool, tuple[tuple[str, str], ...]]
PositionKey = tuple[int, ...]


def transcript_key(
    ruleset: Ruleset, turns: Sequence[tuple[Code, Feedback]]
) -> TranscriptKey:
    """Everything a review depends on, and nothing else.

    Notably not the secret. Two games with different secrets that happened to
    produce the same answers are the same analysis, because the analysis only
    ever looks at what the player was told.
    """
    return (
        ruleset.length,
        ruleset.alphabet,
        ruleset.allow_repeats,
        tuple((format_code(guess), str(feedback)) for guess, feedback in turns),
    )


class ReviewCache:
    """Finished reviews, and the positions inside them.

    Two levels, and the second is the one that does the work. Caching whole
    transcripts only helps a player who reloads their own game. Caching
    *positions* helps everyone: two transcripts that diverge on turn three still
    share turns one and two, and the opening position is shared by every game
    ever played on that ruleset.

    Bounded, and cleared wholesale rather than evicted one entry at a time --
    the working set is a daily puzzle's worth of openings, and an LRU would be
    machinery for a problem this does not have.
    """

    def __init__(self, max_entries: int = 4096) -> None:
        self.max_entries = max_entries
        self._reviews: dict[TranscriptKey, object] = {}
        self._positions: dict[
            PositionKey, tuple[float, float, int | None, int | None]
        ] = {}
        self.hits = 0
        self.misses = 0

    def review(self, key: TranscriptKey) -> object | None:
        """A previously computed review, if this exact transcript was seen."""
        found = self._reviews.get(key)
        if found is None:
            self.misses += 1
        else:
            self.hits += 1
        return found

    def remember(self, key: TranscriptKey, reviews: object) -> None:
        """Store a finished review."""
        if len(self._reviews) >= self.max_entries:
            self._reviews.clear()
        self._reviews[key] = reviews

    def position(
        self, survivors: PositionKey
    ) -> tuple[float, float, int | None, int | None] | None:
        """The best available from a position, if it has been searched before."""
        return self._positions.get(survivors)

    def remember_position(
        self,
        survivors: PositionKey,
        best: tuple[float, float, int | None, int | None],
    ) -> None:
        """Store a searched position."""
        if len(self._positions) >= self.max_entries:
            self._positions.clear()
        self._positions[survivors] = best

    def clear(self) -> None:
        """Forget everything. For tests, and for a ruleset change."""
        self._reviews.clear()
        self._positions.clear()
        self.hits = 0
        self.misses = 0
