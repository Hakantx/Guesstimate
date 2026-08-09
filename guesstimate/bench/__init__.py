"""The benchmark harness.

This layer does I/O -- it reads git, writes JSONL, and emits markdown and
charts -- which is why it lives here and not in `core` or `solvers`.

Three things it takes seriously, because each one is a way for a benchmark to
be quietly wrong rather than obviously broken:

1. **Paired sampling.** Every configuration plays the same secrets in the same
   order, and comparisons are per-secret differences rather than differences of
   means. See `PairedDifference`.
2. **Split timings.** The opening move costs ~25x a whole warm game, so it is
   measured once and reported separately instead of being averaged in.
3. **Provenance.** Every results file records the commit, machine, ruleset,
   sample size, and seed that produced it.
"""

from .harness import (
    Config,
    RunResult,
    draw_sample,
    measure_cold_open,
    play_game,
    run_config,
)
from .provenance import Provenance
from .records import GameRecord, RecordStore
from .stats import (
    PairedDifference,
    Summary,
    counting_floor,
    information_floor,
    paired_difference,
    per_secret_guesses,
    summarise,
)

__all__ = [
    "Config",
    "GameRecord",
    "PairedDifference",
    "Provenance",
    "RecordStore",
    "RunResult",
    "Summary",
    "counting_floor",
    "draw_sample",
    "information_floor",
    "measure_cold_open",
    "paired_difference",
    "per_secret_guesses",
    "play_game",
    "run_config",
    "summarise",
]
