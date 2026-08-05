# Guesstimate

A Bulls and Cows solver, game, and research toy.

The secret is a 4-digit number using the digits 1-9, with no zeros and no
repeated digits — exactly 9x8x7x6 = **3024** possible secrets. You think of
one, the solver finds it.

Feedback on a guess is written `+B-C`:

- **B** — digits correct and in the correct position
- **C** — digits present in the secret but in a different position

If the secret is `1234` and the guess is `3264`, the answer is `+2-1`: the `2`
and the `4` are in the right place, the `3` is present but misplaced.

There are 14 distinct feedback outcomes. `+3-1` is not one of them — if three
digits are correctly placed, the fourth has nowhere else to be.

## Status

Rebuild in progress.

The original was written in high school in 2021 by **Akif Celepcikay**. The
2026 rebuild is by **Hakan Celepcikay**.

That original 138-line script is preserved at `legacy/Game.py` and tagged
[`v1.0-original`](../../tree/v1.0-original). It is kept for the record and is
never modified.

| Phase | | |
|---|---|---|
| 0 | Preserve and scaffold | done |
| 1 | The engine | done |
| 2 | Solvers | done |
| 3 | Benchmark suite | in progress |
| 4 | CLI | |
| 5 | Make it fast | |
| 6 | API and game server | |
| 7 | The web app | |
| 8 | Game review | |
| 9 | Shareability | |
| 10 | LLM evaluation | |
| 11 | Ship | |

Build order is in `ROADMAP.md`, feature specs in `FEATURES.md`, visual
direction in `DESIGN.md`.

## Development

Requires [uv](https://docs.astral.sh/uv/).

```sh
make install    # sync dependencies into .venv
make check      # lint + types + tests, the same set CI runs
```

Individual targets: `make lint`, `make fmt`, `make types`, `make test`,
`make test-fast`, `make cov`. Run `make help` for the full list.

## Benchmarks

**Strategy is very nearly irrelevant on the classic game, and starts to matter
when each guess tells you less.**

On the standard 4-digit, 1-9, no-repeats ruleset, four solvers that range from
"pick any candidate at random" to a full minimax search land within a quarter of
a guess of each other, and not one of them separates from the random baseline at
95% confidence:

| Solver | Mean | Sample max | vs random | 95% CI | Significant |
|---|---|---|---|---|---|
| minimax | 4.870 | 7 | +0.250 | [-0.040, +0.540] | no |
| expected-size | 4.920 | 7 | +0.200 | [-0.081, +0.481] | no |
| entropy | 4.970 | 7 | +0.150 | [-0.112, +0.412] | no |
| random | 5.120 | 7 | — | — | — |

<sub>100 paired secrets of 3024, seed 20260805. Information floor 3.037.</sub>

Move to a ruleset where a guess carries less information — 5 positions over 4
symbols with repeats, so 1024 codes but a similar number of feedback outcomes —
and the same four solvers pull apart cleanly, all three strategies clearing the
bar:

| Solver | Mean | Sample max | vs random | 95% CI | Significant |
|---|---|---|---|---|---|
| entropy | 3.893 | 5 | **+0.258** | [+0.173, +0.343] | **yes** |
| expected-size | 3.930 | 5 | **+0.221** | [+0.144, +0.298] | **yes** |
| minimax | 4.030 | 6 | **+0.121** | [+0.034, +0.208] | **yes** |
| random | 4.151 | 7 | — | — | — |

<sub>300 paired secrets of 1024, seed 20260805. Information floor 2.310.</sub>

The reason is that 3024 candidates against 14 possible answers collapse fast
enough that almost any consistent guess is nearly as good as the best one. The
classic game does not have room for cleverness. That is a more interesting
result than a table of four nearly identical numbers, and it is why the
benchmark reports a second ruleset at all.

`Sample max` is the hardest secret *drawn*, not the true worst case — a mean is
estimable from a sample and a maximum is not, which matters most for minimax,
whose whole justification is the worst case. Run with `--full` for a figure that
earns the name.

### Running it

```sh
make bench                          # 300 secrets, every solver
make bench ARGS="--sample 50"       # quicker
make bench ARGS="--unrestricted"    # both guessing modes, ~5x slower
make bench ARGS="--full"            # every secret; ~108 min per solver
make bench ARGS="--report-only"     # re-render tables from an existing run
```

Full reports and charts land in [`docs/benchmarks/`](docs/benchmarks/). Three
things the harness insists on:

- **Paired sampling.** Every solver plays the same seeded secrets in the same
  order, and comparisons are per-secret differences rather than differences of
  means. Between two strategies that removes most of the variance; against the
  random baseline it removes almost none, for reasons worth reading in
  [`docs/notes/paired-sampling.md`](docs/notes/paired-sampling.md).
- **Split timings.** The opening move costs ~50s on the classic ruleset and
  every game after it ~2s, so the two are reported separately rather than
  averaged into a per-game figure that describes neither.
- **Provenance.** Every report carries the commit, machine, Python version,
  ruleset, sample size, and seed that produced it. Runs are resumable and refuse
  to append to a file written by a different run.

## License

MIT — see `LICENSE`.
