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
| 3 | Benchmark suite | done |
| 4 | CLI | done |
| 5 | Make it fast | done |
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

### Checked against published optima

The standard variant of this game — four positions, digits 0-9, no repeats,
5040 secrets — has two proved bounds, one for each thing a solver could be
optimising. Every secret played by every solver, against both:

| Solver | Mean | vs optimal 5.213 | Worst | vs optimal 7 |
|---|---|---|---|---|
| entropy | 5.314 | +0.101 (**+1.9%**) | 8 | +1 (**+14%**) |
| expected-size | 5.319 | +0.106 (+2.0%) | 8 | +1 (+14%) |
| minimax | 5.354 | +0.141 (+2.7%) | 8 | +1 (+14%) |
| random | 5.458 | +0.245 (+4.7%) | 9 | +2 (+29%) |

<sub>All 5040 secrets, seed 20260805. Optimal mean 5.213 (Tanaka, 1996);
optimal worst case 7 guesses, necessary and sufficient (Chen, Lin and Nguyen,
*Strategy optimization for deductive games*, EJOR). The two bounds optimise
different objectives and are not claimed to be attainable by one strategy.</sub>

**Greedy play is within 2% of optimal on average and a full guess off at the
tail.** Every solver here is greedy: it picks whatever guess splits the current
candidate set best and never considers the position that leaves behind. The
bounds come from optimising a whole game tree, which can mean playing a locally
worse guess now to avoid a bad split two turns later.

That gap has the shape local optimisation predicts. A greedy choice is a small
mistake most of the time, and small mistakes wash out over five thousand games —
hence 2% on the mean. The worst case averages nothing: it is the single deepest
branch, reached by a run of positions where the locally best guess was not the
globally best one, each choice defensible and the accumulation fatal. Greedy
mistakes rarely matter on average precisely because they are rare, and the tail
is where the rare things all happened at once.

### Two lower bounds, both sound

The obvious floor is information-theoretic: log2(5040)/log2(14) = **3.230**
guesses, assuming every guess splits the space perfectly evenly. It is true and
nearly useless — no single code splits 5040 candidates into fourteen equal
parts, let alone repeatedly — and it understates the achievable 5.213 by over
60%.

Counting decision trees does much better. Each node of a strategy has exactly
one winning edge, so at most 13 that continue, and at most `13 ** (j-1)` secrets
can be solved on guess `j`. Packing 5040 as shallowly as those caps allow —
2,380 through depth 4, the remaining 2,660 at depth 5 — gives **4.489**, closing
63% of the gap to optimal.

That bound is valid where a tempting entropy-based tightening was not, and for
the same reason: it uses nothing about any position. The rejected attempt, and
the measurement that killed it, are in
[`docs/notes/`](docs/notes/minimax-mean-vs-worst.md).

| Bound | 5040 variant | Nature |
|---|---|---|
| entropy floor | 3.230 | sound, very loose |
| counting floor | 4.489 | sound, 63% tighter |
| attainable (Tanaka) | 5.213 | proved achievable |
| best solver here | 5.314 | greedy |

### Strategy barely matters on the default ruleset

The project's default excludes zero, giving 3024 secrets. There, four solvers
ranging from "pick any candidate at random" to full minimax land within a
quarter of a guess of each other:

| Solver | Mean | Worst |
|---|---|---|
| entropy | 5.008 | 7 |
| expected-size | 5.011 | 7 |
| minimax | 5.044 | 7 |
| random | 5.161 | 9 |

<sub>All 3024 secrets, seed 20260805. No published bound covers this variant.</sub>

3024 candidates against 14 possible answers collapse fast enough that almost any
consistent guess is nearly as good as the best one. Move to a ruleset where a
guess carries less information — 5 positions over 4 symbols with repeats, 1024
codes — and the same solvers separate cleanly, all three strategies beating the
baseline at 95% confidence. Details in
[`docs/notes/`](docs/notes/minimax-mean-vs-worst.md).

Minimax is worth a specific note: it ties on worst case and loses on mean, on
both variants, so there is no column in which it wins. The guarantee it offers
is real but not exclusive.

## Making it fast

The solvers are naive by construction — every guess scored against every
surviving candidate, every turn — so that the optimisation could be measured
honestly against them. Phase 5 precomputes the full feedback matrix once and
indexes it instead.

| | Naive | Matrix | |
|---|---|---|---|
| Opening move | 58.01s | 0.08s | **748x** |
| Full 3024-secret minimax sweep | 6329s | 37s | **171x** |
| Full sweep, expected-size | 5772s | 39s | 148x |

The opening is the headline. Turn one scores all 3024 guesses against all 3024
candidates while turn two works on the couple of hundred that survived, so it
was 99.5% of a naive game's cost and is now effectively free. The whole-sweep
figure is smaller only because what remains is the leftovers.

Every guess count is byte-identical between the two engines across all 3024
games per solver — the matrix changes speed and nothing else, and a
turn-by-turn equivalence test enforces that rather than merely comparing final
answers. It caught two real bugs doing so, one of which is
[the best finding in the project](docs/notes/float-associativity-tiebreak.md).

The matrix is n² bytes and n²/2 scorings, capped on both. Measured at 6.2µs per
scored pair, time binds first for every ruleset that fits in memory at all, so
the memory ceiling is a backstop rather than a co-equal gate.

### Running it

```sh
make bench                          # 300 secrets, every solver
make bench ARGS="--full"            # every secret
make bench ARGS="--unrestricted"    # both guessing modes
make bench ARGS="--engine pure"     # time the naive path
make bench ARGS="--report-only"     # re-render tables from an existing run
```

Full reports and charts land in [`docs/benchmarks/`](docs/benchmarks/). Three
things the harness insists on:

- **Paired sampling.** Every solver plays the same seeded secrets in the same
  order, and comparisons are per-secret differences rather than differences of
  means. Between two strategies that removes most of the variance; against the
  random baseline it removes almost none, for reasons worth reading in
  [`docs/notes/paired-sampling.md`](docs/notes/paired-sampling.md).
- **Split timings.** The opening move and the games after it are reported
  separately rather than averaged into a per-game figure describing neither.
- **Provenance.** Every report carries the commit, machine, Python version,
  ruleset, sample size, seed, and engine that produced it. Runs are resumable
  and refuse to append to a file written by a different run.

## License

MIT — see `LICENSE`.
