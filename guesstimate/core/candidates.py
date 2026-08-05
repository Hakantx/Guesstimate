"""Enumerating the candidate space, narrowing it, and listing the outcomes."""

import itertools

from .code import Code
from .feedback import Feedback
from .ruleset import Ruleset
from .scoring import score


def all_candidates(ruleset: Ruleset) -> list[Code]:
    """Every code the ruleset allows, in alphabet order.

    Built by permuting or repeating the alphabet directly, never by walking a
    numeric range and filtering it -- a range assumes the symbols are digits,
    which stops being true the moment hex mode exists.

    The order is stable and follows `ruleset.alphabet`, so a candidate's index
    is a meaningful id: the web grid in DESIGN.md lays cells out in exactly this
    order, and Phase 5 indexes the feedback matrix by it.
    """
    if ruleset.allow_repeats:
        return list(itertools.product(ruleset.alphabet, repeat=ruleset.length))
    return list(itertools.permutations(ruleset.alphabet, ruleset.length))


def filter_candidates(
    candidates: list[Code], guess: Code, feedback: Feedback
) -> list[Code]:
    """Keep the candidates still consistent with an answer.

    A candidate survives when, had it been the secret, it would have produced
    exactly this feedback for this guess. Relative order is preserved.
    """
    return [
        candidate for candidate in candidates if score(candidate, guess) == feedback
    ]


def feedback_space(ruleset: Ruleset) -> list[Feedback]:
    """Every outcome actually reachable under a ruleset, ascending.

    For the classic ruleset this is the 14 outcomes. Sorted by `(bulls, cows)`
    and deduplicated, so a position in this list is a stable id -- Phase 5
    encodes the feedback matrix as `uint8` indices into it.

    This is O(size of the candidate space); hoist it out of loops rather than
    calling it per turn.
    """
    # Why (length - 1, 1) is impossible
    # ---------------------------------
    # Say a guess scores length - 1 bulls: every position matches but one. Call
    # the secret's symbol at that odd position s and the guess's g. They differ,
    # or it would have been a bull too.
    #
    # Count the shared symbols. The matched positions contribute length - 1. Can
    # anything else be shared? For any symbol x, the secret holds it
    # (times it was matched) + (1 if s is x), and the guess holds it
    # (times it was matched) + (1 if g is x). The shared count is the smaller of
    # the two, which exceeds the matched count only if x is both s and g -- and
    # s is not g. So the total shared is exactly length - 1.
    #
    # Then cows = shared - bulls = (length - 1) - (length - 1) = 0. One bull short
    # of a win forces zero cows, for every ruleset, repeats or not. For the
    # classic game, 15 pairs satisfy bulls + cows <= 4; punching out (3, 1)
    # leaves 14.
    #
    # Which outcomes the rest of the triangle actually reaches depends on the
    # alphabet -- with two symbols and repeats on, most of it is unreachable --
    # so this function measures rather than assumes, using the shortcut below.
    #
    # Relabelling symmetry
    # --------------------
    # Renaming symbols cannot change a score, because scoring only ever asks
    # whether two symbols are equal, never which symbol they are. So for any
    # permutation p of the alphabet, score(p(secret), p(guess)) == score(secret,
    # guess), and therefore score(p(secret), guess) == score(secret, p'(guess))
    # where p' is the inverse. As guess runs over the whole space, so does
    # p'(guess) -- meaning a secret and any relabelling of it reach the same set
    # of outcomes.
    #
    # One secret per relabelling class is therefore enough. The canonical member
    # of a class is the one whose symbols first appear in alphabet order: 1123
    # is canonical, 2231 is the same pattern wearing different names. With
    # repeats off there is exactly one such code, so the classic game costs a
    # single pass over the candidates instead of 3024 x 3024.
    candidates = all_candidates(ruleset)
    outcomes = set()
    for secret in candidates:
        if not _is_canonical(secret, ruleset.alphabet):
            continue
        for guess in candidates:
            outcomes.add(score(secret, guess))
    return sorted(outcomes, key=lambda feedback: (feedback.bulls, feedback.cows))


def _is_canonical(code: Code, alphabet: str) -> bool:
    seen: set[str] = set()
    for symbol in code:
        if symbol not in seen:
            # A new symbol has to be the next unused one in alphabet order.
            if symbol != alphabet[len(seen)]:
                return False
            seen.add(symbol)
    return True
