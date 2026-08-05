"""Charts. Imported lazily so the test suite never pays for matplotlib."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from .stats import Summary, paired_difference


def write_charts(
    summaries: Sequence[Summary],
    guess_counts: dict[str, list[int]],
    baseline: str,
    floor: float,
    directory: Path,
) -> list[Path]:
    """Emit every figure, returning what was written.

    matplotlib is imported here rather than at module scope so that importing
    `guesstimate.bench` -- which the tests do -- does not drag in a plotting
    stack that most of the suite never touches.
    """
    import matplotlib

    matplotlib.use("Agg")  # no display on CI, and none wanted locally either
    import matplotlib.pyplot as plt

    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    ordered = sorted(summaries, key=lambda s: s.mean)

    # 1. Distribution of guess counts.
    figure, axes = plt.subplots(figsize=(8, 4.5))
    all_counts = sorted({c for s in ordered for c in s.distribution})
    width = 0.8 / len(ordered)
    for offset, summary in enumerate(ordered):
        total = sum(summary.distribution.values())
        shares = [summary.distribution.get(c, 0) / total for c in all_counts]
        positions = [c + offset * width - 0.4 for c in all_counts]
        axes.bar(positions, shares, width=width, label=summary.config)
    axes.set_xlabel("guesses to win")
    axes.set_ylabel("share of games")
    axes.set_title("Guess count distribution")
    axes.set_xticks(all_counts)
    axes.legend(fontsize=8)
    figure.tight_layout()
    path = directory / "guess-distribution.png"
    figure.savefig(path, dpi=140)
    plt.close(figure)
    written.append(path)

    # 2. Candidate collapse, log scale -- the interesting part is the first
    #    turn, which drops by two orders of magnitude and flattens everything
    #    else on a linear axis.
    figure, axes = plt.subplots(figsize=(8, 4.5))
    for summary in ordered:
        turns = range(1, len(summary.collapse) + 1)
        axes.plot(turns, summary.collapse, marker="o", label=summary.config)
    axes.set_yscale("log")
    axes.set_xlabel("guesses made")
    axes.set_ylabel("candidates still possible (mean)")
    axes.set_title("Candidate collapse")
    axes.grid(True, which="both", alpha=0.25)
    axes.legend(fontsize=8)
    figure.tight_layout()
    path = directory / "candidate-collapse.png"
    figure.savefig(path, dpi=140)
    plt.close(figure)
    written.append(path)

    # 3. Paired differences with 95% intervals. Error bars are the point of the
    #    chart: a bar whose interval crosses zero has not shown anything.
    contenders = [s.config for s in ordered if s.config != baseline]
    if contenders:
        figure, axes = plt.subplots(figsize=(8, 4.5))
        means, errors = [], []
        for name in contenders:
            paired = paired_difference(guess_counts[baseline], guess_counts[name])
            means.append(paired.mean)
            errors.append(1.96 * paired.stderr)
        axes.barh(contenders, means, xerr=errors, capsize=4)
        axes.axvline(0, color="black", linewidth=1)
        axes.set_xlabel(f"mean guesses saved vs {baseline} (95% CI)")
        axes.set_title("Paired difference per secret")
        figure.tight_layout()
        path = directory / "paired-difference.png"
        figure.savefig(path, dpi=140)
        plt.close(figure)
        written.append(path)

    # 4. Mean against the information floor.
    figure, axes = plt.subplots(figsize=(8, 4.5))
    axes.bar([s.config for s in ordered], [s.mean for s in ordered])
    axes.axhline(floor, color="crimson", linestyle="--", label=f"floor {floor:.3f}")
    axes.set_ylabel("mean guesses")
    axes.set_title("Mean guesses against the information-theoretic floor")
    axes.tick_params(axis="x", labelrotation=20, labelsize=8)
    axes.legend(fontsize=8)
    figure.tight_layout()
    path = directory / "mean-vs-floor.png"
    figure.savefig(path, dpi=140)
    plt.close(figure)
    written.append(path)

    return written
