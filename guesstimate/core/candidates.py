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
    # Which secrets need scoring is the whole cost of this function, and
    # `relabelling_representatives` answers it -- see there for why one secret
    # per class is enough.
    candidates = all_candidates(ruleset)
    outcomes = set()
    for secret in relabelling_representatives(ruleset):
        for guess in candidates:
            outcomes.add(score(secret, guess))
    return sorted(outcomes, key=lambda feedback: (feedback.bulls, feedback.cows))


def relabelling_representatives(ruleset: Ruleset) -> list[Code]:
    """One secret per relabelling class, in candidate order.

    Renaming symbols cannot change a score, because scoring only ever asks
    whether two symbols are equal, never which symbol they are. So for any
    permutation p of the alphabet, `score(p(secret), p(guess))` equals
    `score(secret, guess)`, and therefore `score(p(secret), guess)` equals
    `score(secret, p'(guess))` where p' is the inverse. As `guess` runs over the
    whole space, so does `p'(guess)` -- so a secret and any relabelling of it
    reach exactly the same set of outcomes, and scoring one member of a class
    stands in for scoring all of them.

    A code represents its class when each symbol's first appearance is the
    earliest alphabet symbol not yet used. So 1123 is a representative and 2231
    is not, being the same "one symbol twice, then two new ones" pattern wearing
    different names.

    How much this saves depends entirely on repeats. With them off, every code
    is the same pattern -- all symbols distinct -- so there is exactly one
    representative and the classic game scores 3024 pairs instead of 3024 x 3024.
    With them on, the count is the number of ways to partition the positions into
    at most `len(alphabet)` groups: 15 for length 4, 41 for length 5 over three
    symbols. Still a large saving, but no longer a constant one.
    """
    return [
        code
        for code in all_candidates(ruleset)
        if _is_canonical(code, ruleset.alphabet)
    ]


def _is_canonical(code: Code, alphabet: str) -> bool:
    seen: set[str] = set()
    for symbol in code:
        if symbol not in seen:
            # A new symbol has to be the next unused one in alphabet order.
            if symbol != alphabet[len(seen)]:
                return False
            seen.add(symbol)
    return True
