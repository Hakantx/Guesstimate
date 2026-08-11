"""Exhaustive game-tree search, for measuring how much greedy play costs.

Small rulesets only. The point is to compute a bound that cannot be measured
by sampling: what an *optimal* adversary could force, against which the greedy
one shipped in `guesstimate.game` can be compared.
"""

from __future__ import annotations

from functools import cache

from guesstimate.core import (
    Code,
    Feedback,
    Ruleset,
    all_candidates,
    feedback_space,
    score,
)


class Tree:
    """Both players' optimal lines over one ruleset."""

    def __init__(self, ruleset: Ruleset) -> None:
        self.ruleset = ruleset
        self.space = tuple(all_candidates(ruleset))
        outcomes = feedback_space(ruleset)
        self.rank = {outcome: index for index, outcome in enumerate(outcomes)}
        # All bulls sorts last in the feedback space, so it is the maximum.
        self.win = max(outcomes, key=lambda o: (o.bulls, o.cows))

    def blocks(
        self, survivors: tuple[Code, ...], guess: Code
    ) -> dict[Feedback, tuple[Code, ...]]:
        """Partition the survivors by the answer `guess` would draw from each."""
        grouped: dict[Feedback, list[Code]] = {}
        for candidate in survivors:
            grouped.setdefault(score(candidate, guess), []).append(candidate)
        return {outcome: tuple(block) for outcome, block in grouped.items()}

    def greedy_reply(self, parts: dict[Feedback, tuple[Code, ...]]) -> Feedback:
        """What `LocalEvilGame` answers: largest block, ties by outcome order."""
        return min(parts, key=lambda o: (-len(parts[o]), self.rank[o]))

    def against_optimal(self) -> int:
        """Guesses a perfect player needs against a perfect adversary."""

        @cache
        def value(survivors: tuple[Code, ...]) -> int:
            if len(survivors) == 1:
                return 1
            best: int | None = None
            for guess in self.space:
                parts = self.blocks(survivors, guess)
                # A guess every survivor answers identically teaches nothing;
                # a player would not ask it, and counting it would make the
                # value infinite for no reason.
                if len(parts) == 1 and next(iter(parts)) != self.win:
                    continue
                worst = max(
                    0 if outcome == self.win else value(block)
                    for outcome, block in parts.items()
                )
                best = 1 + worst if best is None else min(best, 1 + worst)
            assert best is not None
            return best

        return value(self.space)

    def against_greedy(self) -> int:
        """Guesses a perfect player needs against the greedy adversary."""

        @cache
        def value(survivors: tuple[Code, ...]) -> int:
            if len(survivors) == 1:
                return 1
            best: int | None = None
            for guess in self.space:
                parts = self.blocks(survivors, guess)
                reply = self.greedy_reply(parts)
                if parts[reply] == survivors:
                    continue
                cost = 0 if reply == self.win else value(parts[reply])
                best = 1 + cost if best is None else min(best, 1 + cost)
            assert best is not None
            return best

        return value(self.space)

    def best_line(self, survivors: tuple[Code, ...]) -> Code:
        """The player's best guess against the greedy adversary, from here."""

        @cache
        def search(state: tuple[Code, ...]) -> tuple[int, Code]:
            if len(state) == 1:
                return 1, state[0]
            best: tuple[int, Code] | None = None
            for guess in self.space:
                parts = self.blocks(state, guess)
                reply = self.greedy_reply(parts)
                if parts[reply] == state:
                    continue
                cost = 0 if reply == self.win else search(parts[reply])[0]
                if best is None or 1 + cost < best[0]:
                    best = (1 + cost, guess)
            assert best is not None
            return best

        return search(survivors)[1]
