"""`make bench` -- run the sweep and regenerate every number and chart."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from guesstimate.core import Ruleset
from guesstimate.solvers import SOLVERS

from .charts import write_charts
from .harness import Config, RunResult, draw_sample, run_config
from .provenance import Provenance
from .records import RecordStore
from .report import build_report
from .stats import information_floor, per_secret_guesses, summarise

DEFAULT_SAMPLE = 300
DEFAULT_SEED = 20260805


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Command line for the benchmark harness."""
    parser = argparse.ArgumentParser(prog="guesstimate.bench")
    parser.add_argument(
        "--sample",
        type=int,
        default=DEFAULT_SAMPLE,
        help=(
            "secrets to play per configuration (default 300). The naive "
            "solvers cost ~2s per warm game on the classic ruleset, so a full "
            "3024 sweep is ~108 minutes each; pairing makes 300 plenty."
        ),
    )
    parser.add_argument(
        "--full", action="store_true", help="play every secret, ignoring --sample"
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--length", type=int, default=4)
    parser.add_argument("--alphabet", default="123456789")
    parser.add_argument("--repeats", action="store_true")
    parser.add_argument(
        "--solvers",
        nargs="+",
        default=list(SOLVERS),
        help="which strategies to run (default all)",
    )
    parser.add_argument(
        "--unrestricted",
        action="store_true",
        help=(
            "also run every scoring solver allowed to guess outside the "
            "surviving set. Roughly 4.6x slower per game."
        ),
    )
    parser.add_argument("--baseline", default=None)
    parser.add_argument(
        "--engine",
        choices=["pure", "matrix", "auto"],
        default="auto",
        help=(
            "which partitioner to time against. 'auto' takes the matrix when "
            "the ruleset can afford one and falls back to on-demand scoring "
            "when it cannot; the choice is recorded in every config name."
        ),
    )
    parser.add_argument(
        "--baseline-repeats",
        type=int,
        default=5,
        help=(
            "games per secret for stochastic solvers (default 5). One game is "
            "a single draw whose per-secret value correlates with nothing, so "
            "pairing against it recovers no variance; averaging several turns "
            "it into an estimate of expected performance on that secret. "
            "Deterministic solvers ignore this."
        ),
    )
    parser.add_argument("--out", type=Path, default=Path("docs/benchmarks"))
    parser.add_argument(
        "--no-charts", action="store_true", help="skip matplotlib output"
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help=(
            "rebuild tables and charts from an existing games.jsonl without "
            "playing anything. Use after changing the analysis, not the data."
        ),
    )
    return parser.parse_args(argv)


def resolve_engine(requested: str, ruleset: Ruleset) -> str:
    """Pick the partitioner, reporting the estimate before any long build."""
    if requested != "auto":
        return requested
    from guesstimate.data import estimate

    costs = estimate(ruleset)
    print(costs.describe(), flush=True)
    return "matrix" if costs.affordable else "pure"


def configurations(
    names: list[str], unrestricted: bool, engine: str = "pure"
) -> list[Config]:
    """Expand solver names into the configurations to run."""
    configs = [Config(name, True, engine) for name in names]
    if unrestricted:
        # RandomSolver documents that it ignores the flag, so running it
        # unrestricted would duplicate a row rather than measure anything.
        configs += [Config(n, False, engine) for n in names if n != "random"]
    return configs


def main(argv: list[str] | None = None) -> int:
    """Run the sweep, write the report, and return a shell exit code."""
    args = parse_args(argv)
    ruleset = Ruleset(
        length=args.length, alphabet=args.alphabet, allow_repeats=args.repeats
    )
    size = None if args.full else args.sample
    sample = draw_sample(ruleset, size, args.seed)
    provenance = Provenance.capture(ruleset, len(sample), args.seed, args.out)

    args.out.mkdir(parents=True, exist_ok=True)
    if args.report_only:
        store = RecordStore.open_for_reading(args.out / "games.jsonl")
        provenance = store.provenance
        # The run's own ruleset, not whatever the flags happen to say. A stored
        # run already records what it played; re-deriving it from CLI defaults
        # meant re-rendering a report required retyping the original flags
        # exactly, and getting them wrong produced either a crash or, worse, a
        # correct-looking report built against the wrong space.
        ruleset = Ruleset(
            length=provenance.ruleset["length"],
            alphabet=provenance.ruleset["alphabet"],
            allow_repeats=provenance.ruleset["allow_repeats"],
        )
        sample = draw_sample(ruleset, provenance.sample_size, provenance.seed)
    else:
        store = RecordStore(args.out / "games.jsonl", provenance)

    engine = resolve_engine(args.engine, ruleset)
    configs = configurations(args.solvers, args.unrestricted, engine)
    print(
        f"{len(configs)} configurations x {len(sample)} secrets, "
        f"seed {args.seed}, {ruleset.space_size}-code ruleset",
        flush=True,
    )

    summaries = []
    # Whether every secret is played decides whether the maximum guess count
    # is *the* worst case or merely the worst one drawn -- and the console
    # summary has to use the same word the published table does.
    exhaustive = len(sample) == ruleset.space_size
    guess_counts: dict[str, list[float]] = {}
    started = time.perf_counter()
    for config in configs:
        config_started = time.perf_counter()
        if args.report_only:
            kept = [r for r in store.records() if r.config == config.name]
            if not kept:
                continue
            result = RunResult(config=config, records=kept, cold_open_seconds=0.0)
        else:
            result = run_config(
                config,
                ruleset,
                sample,
                args.seed,
                store=store,
                progress=True,
                repeats=args.baseline_repeats,
            )
        summary = summarise(result)
        summaries.append(summary)
        guess_counts[config.name] = per_secret_guesses(result.records)
        print(
            f"{config.name}: mean {summary.mean:.3f}, "
            f"{'worst' if exhaustive else 'sample max'} {summary.worst}, "
            f"cold open {summary.cold_open_seconds:.1f}s, "
            f"{time.perf_counter() - config_started:.0f}s total",
            flush=True,
        )

    floor = information_floor(ruleset)
    default_baseline = f"random/restricted/{engine}"
    wanted = args.baseline or default_baseline
    baseline = wanted if wanted in guess_counts else configs[0].name
    report = build_report(
        provenance,
        ruleset,
        summaries,
        guess_counts,
        floor,
        baseline,
        exhaustive=exhaustive,
    )
    (args.out / "README.md").write_text(report, encoding="utf-8")
    print(f"wrote {args.out / 'README.md'}")

    if not args.no_charts:
        for path in write_charts(summaries, guess_counts, baseline, floor, args.out):
            print(f"wrote {path}")

    print(f"done in {(time.perf_counter() - started) / 60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
