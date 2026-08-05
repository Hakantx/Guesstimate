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

```sh
make bench                          # 300 secrets, every solver
make bench ARGS="--sample 50"       # quicker
make bench ARGS="--unrestricted"    # both guessing modes, ~4.6x slower
```

Results land in [`docs/benchmarks/`](docs/benchmarks/) — a markdown report plus
charts, regenerated from scratch every run. Three things the harness insists on:

- **Paired sampling.** Every solver plays the same seeded secrets in the same
  order, and comparisons are per-secret differences rather than differences of
  means. Guess counts vary by whole turns between secrets while the gap between
  good strategies is under a tenth of a turn, so unpaired means cannot see it.
- **Split timings.** The opening move costs tens of seconds and every game after
  it about two, so the two are reported separately rather than averaged into a
  per-game figure that describes neither.
- **Provenance.** Every report carries the commit, machine, Python version,
  ruleset, sample size, and seed that produced it. Runs are resumable and refuse
  to continue into a file written by a different run.

## License

MIT — see `LICENSE`.
