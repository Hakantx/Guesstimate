"""Ruleset grid: does the entropy-vs-random lead track alphabet, space, or outcomes?

Space size is held near-constant (1000-3125) while alphabet size and length
trade off against each other, so the three candidate predictors are no longer
confounded the way they were across the two rulesets measured so far.
"""

import json
import statistics
import time

from guesstimate.bench import (
    Config,
    Provenance,
    draw_sample,
    information_floor,
    paired_difference,
    per_secret_guesses,
    run_config,
)
from guesstimate.core import Ruleset, feedback_space

SEED = 20260805
SAMPLE = 300
REPEATS = 5

GRID = [
    (Ruleset(5, "1234", allow_repeats=True), "a4 L5 rep"),
    (Ruleset(5, "12345", allow_repeats=True), "a5 L5 rep"),
    (Ruleset(4, "123456", allow_repeats=True), "a6 L4 rep"),
    (Ruleset(4, "123456789"), "a9 L4 norep (classic)"),
    (Ruleset(3, "0123456789", allow_repeats=True), "a10 L3 rep"),
]

results = []
for ruleset, label in GRID:
    started = time.perf_counter()
    outcomes = len(feedback_space(ruleset))
    sample = draw_sample(ruleset, SAMPLE, SEED)

    baseline = run_config(
        Config("random", True), ruleset, sample, seed=SEED, repeats=REPEATS
    )
    entropy = run_config(Config("entropy", True), ruleset, sample, seed=SEED)

    base = per_secret_guesses(baseline.records)
    cont = per_secret_guesses(entropy.records)
    paired = paired_difference(base, cont)
    low, high = paired.confidence_interval

    row = {
        "label": label,
        "alphabet": len(ruleset.alphabet),
        "length": ruleset.length,
        "repeats": ruleset.allow_repeats,
        "space": ruleset.space_size,
        "outcomes": outcomes,
        "floor": information_floor(ruleset),
        "random_mean": statistics.mean(base),
        "entropy_mean": statistics.mean(cont),
        "lead": paired.mean,
        "lead_sd": paired.stdev,
        "ci_low": low,
        "ci_high": high,
        "significant": paired.is_significant,
        "correlation": statistics.correlation(base, cont),
        "seconds": time.perf_counter() - started,
    }
    results.append(row)
    print(
        f"{label:24s} space={row['space']:5d} a={row['alphabet']:2d} "
        f"outs={outcomes:3d} floor={row['floor']:.2f} "
        f"rand={row['random_mean']:.3f} ent={row['entropy_mean']:.3f} "
        f"lead={paired.mean:+.3f} [{low:+.3f},{high:+.3f}] "
        f"{'SIG' if paired.is_significant else '-  '} ({row['seconds']:.0f}s)",
        flush=True,
    )

provenance = Provenance.capture(GRID[0][0], SAMPLE, SEED)
out = {"provenance": provenance.to_dict(), "sample": SAMPLE, "rows": results}
with open("docs/benchmarks/grid.json", "w", encoding="utf-8") as handle:
    json.dump(out, handle, indent=2)
print("wrote docs/benchmarks/grid.json")
