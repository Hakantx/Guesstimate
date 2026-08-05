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
    parser.add_argument("--baseline", default="random/restricted")
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


def configurations(names: list[str], unrestricted: bool) -> list[Config]:
    """Expand solver names into the configurations to run."""
    configs = [Config(name, True) for name in names]
    if unrestricted:
        # RandomSolver documents that it ignores the flag, so running it
        # unrestricted would duplicate a row rather than measure anything.
        configs += [Config(n, False) for n in names if n != "random"]
    return configs


def main(argv: list[str] | None = None) -> int:
    """Run the sweep, write the report, and return a shell exit code."""
    args = parse_args(argv)
    ruleset = Ruleset(
        length=args.length, alphabet=args.alphabet, allow_repeats=args.repeats
    )
    size = None if args.full else args.sample
    sample = draw_sample(ruleset, size, args.seed)
    provenance = Provenance.capture(ruleset, len(sample), args.seed)

    args.out.mkdir(parents=True, exist_ok=True)
    if args.report_only:
        store = RecordStore.open_for_reading(args.out / "games.jsonl")
        provenance = store.provenance
        sample = draw_sample(ruleset, provenance.sample_size, provenance.seed)
    else:
        store = RecordStore(args.out / "games.jsonl", provenance)

    configs = configurations(args.solvers, args.unrestricted)
    print(
        f"{len(configs)} configurations x {len(sample)} secrets, "
        f"seed {args.seed}, {ruleset.space_size}-code ruleset",
        flush=True,
    )

    summaries = []
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
            f"{config.name}: mean {summary.mean:.3f}, sample max {summary.worst}, "
            f"cold open {summary.cold_open_seconds:.1f}s, "
            f"{time.perf_counter() - config_started:.0f}s total",
            flush=True,
        )

    floor = information_floor(ruleset)
    baseline = args.baseline if args.baseline in guess_counts else configs[0].name
    report = build_report(
        provenance,
        ruleset,
        summaries,
        guess_counts,
        floor,
        baseline,
        exhaustive=len(sample) == ruleset.space_size,
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
