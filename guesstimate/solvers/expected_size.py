"""Optimise the average outcome rather than the worst one."""

from collections.abc import Sequence

from .partition import PartitionSolver


class ExpectedSizeSolver(PartitionSolver):
    """Minimises how many candidates survive on average.

    Every surviving candidate is equally likely to be the secret, so a group of
    size `n` out of `total` is reached with probability `n / total`, and reaching
    it leaves `n` candidates. The expected number left is therefore the sum over
    groups of `(n / total) * n`, which is `sum(n^2) / total`.

    Squaring is what does the work: it punishes one big group far more than
    several middling ones, so this favours even splits. Where minimax asks "how
    bad can this get", this asks "how bad will this usually be", and the two
    disagree exactly when a guess has a good average but one nasty branch.
    """

    def _cost(self, partition_sizes: Sequence[int]) -> float:
        total = sum(partition_sizes)
        return sum(size * size for size in partition_sizes) / total
