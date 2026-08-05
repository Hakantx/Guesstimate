"""Scoring a guess against a secret."""

from collections import Counter

from .code import Code
from .feedback import Feedback


def score(secret: Code, guess: Code) -> Feedback:
    """Score `guess` against `secret`.

    Args:
        secret: The code being guessed at.
        guess: The code offered.

    Returns:
        The bulls and cows for this pair.

    Raises:
        ValueError: If the two codes are different lengths.
    """
    # Why counts instead of a pairwise double-loop
    # --------------------------------------------
    # The obvious implementation walks every guess symbol against every secret
    # symbol and counts hits. That is right only while symbols are unique. With
    # repeats it double-counts: secret 1123 against guess 1213 has two 1s on
    # each side, and a naive loop pairs each guess 1 with each secret 1 and
    # reports more matches than exist.
    #
    # Counting is exact for both cases. For each symbol, the number of copies
    # the two codes genuinely share is min(count in secret, count in guess) --
    # you cannot match more 1s than either side actually has. Summing that over
    # every symbol gives the total shared symbols, ignoring position entirely.
    #
    # Bulls are the positions that agree, and every bull is by definition one of
    # those shared symbols. So the shared ones that are *not* bulls are exactly
    # the cows, and cows = total_shared - bulls. No double counting, and the
    # default no-repeats ruleset is just the easy special case.
    #
    # Note this makes score symmetric: score(a, b) == score(b, a), since both
    # halves only ever ask whether two symbols are equal.
    if len(secret) != len(guess):
        raise ValueError(
            f"codes must be the same length, got {len(secret)} and {len(guess)}"
        )

    bulls = 0
    for secret_symbol, guess_symbol in zip(secret, guess, strict=True):
        if secret_symbol == guess_symbol:
            bulls += 1

    secret_counts = Counter(secret)
    guess_counts = Counter(guess)
    shared = 0
    for symbol, count in guess_counts.items():
        shared += min(count, secret_counts[symbol])

    return Feedback(bulls=bulls, cows=shared - bulls)
