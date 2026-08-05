"""Pick the guess that answers the most bits of the question."""

import math
from collections.abc import Sequence

from .partition import PartitionSolver


class EntropySolver(PartitionSolver):
    """Maximises the information a guess reveals, measured in bits.

    Treat the feedback as a message. Before guessing, the secret is one of
    `total` equally likely candidates; after, it is one of however many share
    the answer received. A group of size `n` arrives with probability
    `p = n / total` and carries `-log2(p)` bits, so the expected yield of a
    guess is the Shannon entropy of its split, `-sum(p * log2 p)`.

    Entropy is highest when the groups are even and numerous, which is the same
    instinct as `ExpectedSizeSolver` measured on a logarithmic scale, and the
    two often choose the same guess. Entropy weighs a rare, hugely informative
    answer more generously than expected-size does.

    **The sign.** `_cost` is minimised by `PartitionSolver`, but information is
    something we want more of, so this returns *negative* entropy. Returning
    entropy unnegated is a real hazard: the solver would still be a legal
    solver, still narrow correctly, still terminate, and still pass every
    conformance test -- while deliberately choosing the guess that reveals the
    least. It would simply be the worst strategy here, quietly. That is why
    there is a test asserting this solver beats the random baseline.
    """

    def _cost(self, partition_sizes: Sequence[int]) -> float:
        total = sum(partition_sizes)
        bits = 0.0
        for size in partition_sizes:
            probability = size / total
            bits -= probability * math.log2(probability)
        return -bits
