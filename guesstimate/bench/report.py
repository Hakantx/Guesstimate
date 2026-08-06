"""Markdown tables, each carrying the provenance of the run behind it."""

from __future__ import annotations

from collections.abc import Sequence

from guesstimate.core import Ruleset

from .provenance import Provenance
from .stats import Summary, paired_difference


def _seconds(value: float) -> str:
    if value >= 1:
        return f"{value:.2f}s"
    return f"{value * 1000:.0f}ms"


def guess_table(
    summaries: Sequence[Summary], ruleset: Ruleset, floor: float, exhaustive: bool
) -> str:
    """Guess counts per configuration, best mean first.

    The worst-case column is named for what it actually is. A mean is estimable
    from a sample; a maximum is not. Over 100 of 3024 secrets every solver
    reported 7, which says the hardest secret *drawn* needed 7 -- not that no
    secret needs 8. Only a full sweep licenses the word "worst".
    """
    worst_header = "Worst" if exhaustive else "Sample max"
    rows = [
        f"| Solver | Mean | Median | {worst_header} | SD | vs floor |",
        "|---|---|---|---|---|---|",
    ]
    for summary in sorted(summaries, key=lambda s: s.mean):
        rows.append(
            f"| `{summary.config}` | {summary.mean:.3f} | {summary.median:.1f} | "
            f"{summary.worst} | {summary.stdev:.3f} | +{summary.mean - floor:.3f} |"
        )
    rows.append("")
    rows.append(
        f"Information floor for this ruleset: **{floor:.3f}** guesses "
        f"(log2({ruleset.space_size}) / log2(outcomes)). No strategy can average "
        f"less; the `vs floor` column is how far each one is from a bound that "
        f"assumes every guess splits the space perfectly evenly."
    )
    if not exhaustive:
        rows.append("")
        rows.append(
            f"**`Sample max` is a lower bound on the true worst case**, not the "
            f"worst case. It is the hardest of the {summaries[0].n} secrets "
            f"drawn, out of {ruleset.space_size}; the real maximum can only be "
            f"higher. This matters most for minimax, whose entire justification "
            f"is the worst case -- the one column a sample cannot produce. Run "
            f'`make bench ARGS="--full"` for a figure that earns the name.'
        )
    return "\n".join(rows)


def timing_table(summaries: Sequence[Summary]) -> str:
    """Cold open and warm games, kept apart."""
    rows = [
        "| Solver | Cold open | Warm game (mean) | Warm game (median) | Per turn |",
        "|---|---|---|---|---|",
    ]
    for summary in sorted(summaries, key=lambda s: s.config):
        rows.append(
            f"| `{summary.config}` | {_seconds(summary.cold_open_seconds)} | "
            f"{_seconds(summary.warm_mean_seconds)} | "
            f"{_seconds(summary.warm_median_seconds)} | "
            f"{_seconds(summary.turn_mean_seconds)} |"
        )
    rows.append("")
    rows.append(
        "Cold open is the first guess of the run, searching the whole space "
        "with an empty opening cache. Every warm game reuses that opening, so "
        "the two are reported apart -- averaging them would fold a single "
        "outlier worth tens of seconds into a per-game figure."
    )
    return "\n".join(rows)


def paired_table(
    baseline: str, results: dict[str, list[float]], contenders: Sequence[str]
) -> str:
    """Paired differences against one baseline, secret by secret."""
    rows = [
        f"| Solver vs `{baseline}` | Mean diff | SD | 95% CI | W/L/T | Significant |",
        "|---|---|---|---|---|---|",
    ]
    for name in contenders:
        if name == baseline:
            continue
        paired = paired_difference(results[baseline], results[name])
        low, high = paired.confidence_interval
        rows.append(
            f"| `{name}` | {paired.mean:+.3f} | {paired.stdev:.3f} | "
            f"[{low:+.3f}, {high:+.3f}] | "
            f"{paired.wins}/{paired.losses}/{paired.ties} | "
            f"{'yes' if paired.is_significant else 'no'} |"
        )
    rows.append("")
    rows.append(
        "Positive means fewer guesses than the baseline. Every solver played "
        "the same secrets in the same order, so these are per-secret "
        "differences rather than differences of means -- which removes the "
        "variation from some secrets simply being harder, and is what makes a "
        "gap of a few hundredths of a guess measurable at all."
    )
    return "\n".join(rows)


def collapse_table(summaries: Sequence[Summary]) -> str:
    """Mean candidates left after each guess."""
    longest = max(len(s.collapse) for s in summaries)
    turns = min(longest, 5)
    header = " | ".join(f"After {i + 1}" for i in range(turns))
    rows = [f"| Solver | {header} |", "|---|" + "---|" * turns]
    for summary in sorted(summaries, key=lambda s: s.config):
        cells = " | ".join(
            f"{summary.collapse[i]:.1f}" if i < len(summary.collapse) else "1.0"
            for i in range(turns)
        )
        rows.append(f"| `{summary.config}` | {cells} |")
    return "\n".join(rows)


def build_report(
    provenance: Provenance,
    ruleset: Ruleset,
    summaries: Sequence[Summary],
    guess_counts: dict[str, list[float]],
    floor: float,
    baseline: str,
    exhaustive: bool = False,
) -> str:
    """Assemble the whole markdown document."""
    names = [s.config for s in summaries]
    parts = [
        "# Benchmarks",
        "",
        "Generated by `make bench`. Every figure here comes from the run "
        "described below; none of it is copied forward from an earlier one.",
        "",
        provenance.to_markdown(),
        "",
        "## Guess counts",
        "",
        guess_table(summaries, ruleset, floor, exhaustive),
        "",
        "## Paired comparison",
        "",
        paired_table(baseline, guess_counts, names),
        "",
        "## Timing",
        "",
        timing_table(summaries),
        "",
        "## Candidate collapse",
        "",
        collapse_table(summaries),
        "",
        "Mean candidates still possible after each guess. The first guess does "
        "most of the work; what separates the strategies is how evenly they "
        "split what is left.",
        "",
    ]
    return "\n".join(parts)
