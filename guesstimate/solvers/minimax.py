"""Make the worst case as good as possible."""

from collections.abc import Sequence

from .partition import PartitionSolver


class MinimaxSolver(PartitionSolver):
    """Minimises the largest group a guess could leave behind.

    Assume the answer will be the most unhelpful one available. A guess splits
    the survivors into groups, one per possible feedback, and whichever group
    the secret falls into is everything that survives the turn. The worst that
    can happen is the largest group, so this picks the guess whose largest group
    is smallest.

    That is a pessimistic reading -- it optimises the worst case rather than the
    average, so it tends to have the best guaranteed ceiling and not the best
    mean. `ExpectedSizeSolver` makes the opposite trade with the same machinery.
    """

    def _cost(self, partition_sizes: Sequence[int]) -> float:
        return float(max(partition_sizes))
