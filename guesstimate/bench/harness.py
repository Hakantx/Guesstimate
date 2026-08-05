"""Playing the games and timing them."""

from __future__ import annotations

import random
import time
from collections.abc import Sequence
from dataclasses import dataclass

from guesstimate.core import Code, Ruleset, all_candidates, score
from guesstimate.solvers import SOLVERS, clear_opening_cache

from .records import GameRecord, RecordStore

# Mixed into the run seed so each game reseeds independently of the ones before
# it. Any odd constant does; this one is prime and large enough that adjacent
# indices do not produce adjacent states.
_INDEX_STRIDE = 1_000_003


@dataclass(frozen=True)
class Config:
    """One solver in one guessing mode."""

    solver: str
    restrict_to_candidates: bool

    @property
    def name(self) -> str:
        """Stable id used in records, tables, and chart legends."""
        mode = "restricted" if self.restrict_to_candidates else "unrestricted"
        return f"{self.solver}/{mode}"


@dataclass(frozen=True)
class RunResult:
    """Everything one configuration produced."""

    config: Config
    records: list[GameRecord]
    cold_open_seconds: float


def draw_sample(ruleset: Ruleset, size: int | None, seed: int) -> list[Code]:
    """Choose the secrets, once, for every solver in the run.

    Drawn without replacement from the full space and returned in draw order,
    so index `i` is the same secret for every configuration. Paired comparison
    depends entirely on that: it is what lets a per-secret difference cancel
    the difficulty of the secret itself.

    `size=None` means the whole space, which is affordable for the cheap
    solvers and after Phase 5 for all of them.
    """
    space = all_candidates(ruleset)
    if size is None:
        return space
    if size > len(space):
        raise ValueError(f"cannot sample {size} secrets from a space of {len(space)}")
    return random.Random(seed).sample(space, size)


def play_game(
    config: Config, ruleset: Ruleset, secret: Code, index: int, seed: int
) -> GameRecord:
    """Play one game and record what it cost.

    The solver is reseeded from the run seed and the *sample index*, never from
    a running counter. That keeps every configuration's game on secret `i`
    identical whether the run started at the beginning or resumed at index 200,
    which is what makes a resumed run comparable to an uninterrupted one.
    """
    solver = SOLVERS[config.solver](
        ruleset,
        restrict_to_candidates=config.restrict_to_candidates,
        rng=random.Random(seed * _INDEX_STRIDE + index),
    )

    turn_seconds: list[float] = []
    survivors: list[int] = []
    started = time.perf_counter()
    while True:
        turn_started = time.perf_counter()
        guess = solver.guess()
        turn_seconds.append(time.perf_counter() - turn_started)

        feedback = score(secret, guess)
        solver.update(guess, feedback)
        survivors.append(len(solver.candidates))
        if feedback.is_win(ruleset.length):
            break

    return GameRecord(
        config=config.name,
        secret_index=index,
        secret="".join(secret),
        guesses=len(turn_seconds),
        seconds=time.perf_counter() - started,
        turn_seconds=tuple(turn_seconds),
        survivors=tuple(survivors),
    )


def measure_cold_open(config: Config, ruleset: Ruleset) -> float:
    """Time the opening search on an empty cache, then leave the cache warm.

    This is the number Phase 5 will halve, and it is reported on its own. It is
    ~52s on the classic ruleset against ~2s for a whole warm game, so folding
    it into a per-game mean over 300 games would bury a 25x outlier inside a
    figure that then gets published as "seconds per game".
    """
    clear_opening_cache()
    solver = SOLVERS[config.solver](
        ruleset,
        restrict_to_candidates=config.restrict_to_candidates,
        rng=random.Random(0),
    )
    started = time.perf_counter()
    solver.guess()
    return time.perf_counter() - started


def run_config(
    config: Config,
    ruleset: Ruleset,
    sample: Sequence[Code],
    seed: int,
    store: RecordStore | None = None,
    start_index: int = 0,
    progress: bool = False,
) -> RunResult:
    """Play every secret in the sample with one configuration.

    The cold open is measured and charged separately before the loop starts, so
    every game in `records` is a warm game and their mean describes the same
    kind of event.
    """
    cold_open = measure_cold_open(config, ruleset)

    already = store.done(config.name) if store else set()
    existing = (
        {r.secret_index: r for r in store.records() if r.config == config.name}
        if store
        else {}
    )

    records: list[GameRecord] = []
    for offset, secret in enumerate(sample):
        index = start_index + offset
        if index in already:
            records.append(existing[index])
            continue

        record = play_game(config, ruleset, secret, index, seed)
        if store:
            store.append(record)
        records.append(record)
        if progress and (offset + 1) % 10 == 0:
            print(f"  {config.name}: {offset + 1}/{len(sample)}", flush=True)

    records.sort(key=lambda r: r.secret_index)
    return RunResult(config=config, records=records, cold_open_seconds=cold_open)
