"""Codebreaking strategies.

Like `core`, this layer is pure: no I/O, no imports beyond `core` and the
stdlib, and portable enough to transcribe into TypeScript (CLAUDE.md rules 1
and 9).

Four strategies, one interface. `Solver` is the contract; `BaseSolver` holds
the candidate bookkeeping they all share; `PartitionSolver` adds the
score-every-split machinery the three non-random ones share. Adding a fifth
means one file and one method.
"""

from .base import BaseSolver
from .entropy import EntropySolver
from .expected_size import ExpectedSizeSolver
from .minimax import MinimaxSolver
from .partition import PartitionSolver, clear_opening_cache
from .protocol import InconsistentFeedbackError, Solver
from .random_solver import RandomSolver

# Keyed by the name the CLI's --solver flag and the API accept. Typed as
# type[BaseSolver] rather than type[Solver]: a Protocol cannot be instantiated,
# so mypy rejects type[Solver] here, and every concrete strategy subclasses
# BaseSolver anyway. Uniform constructors are what let a caller do
# SOLVERS[name](ruleset, **options) without knowing which one it got.
SOLVERS: dict[str, type[BaseSolver]] = {
    "random": RandomSolver,
    "minimax": MinimaxSolver,
    "expected-size": ExpectedSizeSolver,
    "entropy": EntropySolver,
}

__all__ = [
    "SOLVERS",
    "BaseSolver",
    "EntropySolver",
    "ExpectedSizeSolver",
    "InconsistentFeedbackError",
    "MinimaxSolver",
    "PartitionSolver",
    "RandomSolver",
    "Solver",
    "clear_opening_cache",
]
