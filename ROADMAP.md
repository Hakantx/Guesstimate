# Guesstimate — Build Roadmap

Eleven phases. Finish one, merge it, then start the next. Every phase ends with
the repo in a working, demoable state — no phase leaves it half-broken.

Feature specs live in `FEATURES.md`. Visual direction lives in `DESIGN.md`.

---

## Phase 0 — Preserve and scaffold

Tag the current commit `v1.0-original` so the high school version stays
reachable forever. Move `Game.py` to `legacy/Game.py` and never touch it again.

Set up `pyproject.toml` with uv, ruff, mypy strict, pytest. Add a GitHub Actions
workflow running lint, types, and tests on push. Add `.editorconfig`,
`.gitignore`, MIT license, and a stub README.

Nothing here is interesting and it takes an hour, and every later phase is
easier because of it.

**Done when:** CI is green on an empty test suite.

---

## Phase 1 — The engine

`guesstimate/core/`. This is the foundation and it must be generic.

```python
@dataclass(frozen=True)
class Ruleset:
    length: int = 4
    alphabet: str = "123456789"   # hex mode: "0123456789ABCDEF"
    allow_repeats: bool = False
```

Build:

- `Code` — a tuple of symbols. Not a string, not an int. Ints break the moment
  leading zeros or hex are allowed.
- `Feedback` — a frozen `(bulls, cows)` pair with `parse()` and `__str__()` so
  `+2-1` round-trips exactly.
- `score(secret, guess) -> Feedback` — count-based (see CLAUDE.md), correct
  for repeats even though the default ruleset forbids them.
- `all_candidates(ruleset)` — `itertools.permutations` when repeats are off,
  `itertools.product` when they're on. Never build a numeric range and filter.
- `filter_candidates(candidates, guess, feedback)` — keep only the consistent
  ones.
- `feedback_space(ruleset)` — enumerate every reachable `(bulls, cows)` pair.
  For the default ruleset this returns 14. Assert it in a test.

Property tests with Hypothesis:

- bulls + cows never exceeds `ruleset.length`
- `score(x, x)` is all bulls, always
- if `score(secret, guess) == fb`, then `secret` survives
  `filter_candidates(all, guess, fb)`
- over a full randomized playthrough, the true secret is never eliminated
- `Feedback.parse(str(fb)) == fb` for every fb in the feedback space
- `(length - 1, 1)` is never produced — the impossible-outcome property

**Done when:** you can play and win a full game from a Python REPL with no UI.

---

## Phase 2 — Solvers

`guesstimate/solvers/`. A `Solver` protocol plus four implementations.

| Strategy | Chooses the guess that... | Why it's here |
|---|---|---|
| `RandomSolver` | is any surviving candidate, picked at random | the baseline, and what v1 did |
| `MinimaxSolver` | minimizes the largest possible surviving set | Knuth's approach, optimizes worst case |
| `ExpectedSizeSolver` | minimizes the *average* surviving set size | optimizes the mean instead |
| `EntropySolver` | maximizes information gained, in bits | information-theoretic, often ties minimax |

Every solver takes a `restrict_to_candidates: bool` flag. When False it may
guess anything in the full space, including numbers already ruled out.

**Expected, not measured:** the reasoning is that a guess which cannot possibly
win can still split the remaining set better than any guess that can, so
spending a turn on information should pay for itself. That is the standard
argument and it is plausible, but as of Phase 2 nobody here has run it. Both
modes are implemented and tested; neither has been benchmarked against the
other. Until Phase 3 settles it, do not write it down as fact.

Write minimax naively. It will be slow. That is deliberate; Phase 5 measures
the speedup.

Tie-breaking matters and must be deterministic: prefer a guess that is itself
still a candidate, then lowest lexicographic order. Document it, or benchmarks
won't reproduce.

**Done when:** all four solve any secret, and a test asserts none exceeds a
guess ceiling across a sampled sweep of secrets.

---

## Phase 3 — Benchmark suite

`guesstimate/bench/` runs every solver over a set of secrets and reports:

- mean, median, worst case, and standard deviation of guess count
- the full distribution as a histogram
- wall-clock time per game and per turn
- how many candidates survive after guess 1, 2, 3 (the collapse curve)

Emit a markdown table plus matplotlib charts into `docs/benchmarks/`. Wire it
to `make bench`. Seed every random source so runs reproduce.

### Sample size

**The naive solvers benchmark a seeded random sample of 300 secrets, not all
3024.**

Phase 2 measured a scoring solver at roughly 51 seconds per game on the
reference machine, of which turn one was 99.5% — the opening scores all 3024
guesses against all 3024 candidates, and every turn after that works on a few
hundred survivors. Since the opening is identical in every game, Phase 2 caches
it per `(strategy, ruleset, restriction)`. That is bookkeeping, not the Phase 5
matrix work, and it does not spoil that measurement.

Measured over 30 warm games per solver: the first game still costs ~51s, and
every game after it averages **2.13s** (sd 1.62, median 1.38, range 0.02–4.23).
The spread is wide and right-skewed because turn two's cost depends on how many
candidates survived turn one, which varies by secret — so the mean is what the
projections below use, not the median.

| Sweep | Per solver | Three scoring solvers |
|---|---|---|
| 300 secrets | ~11.5 min | ~35 min |
| 3024 secrets | ~108 min | ~5.4 hours |

Sampling is what keeps this a benchmark rather than an afternoon. The standard
error on mean guess count at n=300 is well under a tenth of a turn, far finer
than the gaps between strategies, so nothing worth seeing is lost.

Full 3024-secret sweeps happen after Phase 5, when the feedback matrix makes
them cheap. `RandomSolver` is fast enough to sweep in full at any time.

Every published table states its sample size, its seed, and the machine. A mean
guess count with no n beside it is not a result, and a table that mixes a
300-sample solver with a 3024-sample one without saying so is worse than no
table at all.

Reference hardware is a 2017 dual-core Intel i7. Every published number comes
from that machine. The harness still needs resumable runs and a `--sample N`
flag from the start — 300 is the default, not a ceiling. Two cores also means
process-level parallelism buys about 2x and no more; do not design around a
core count that does not exist. Record the machine alongside the numbers.

### Named deliverable: settle restricted vs unrestricted

Phase 2 shipped the `restrict_to_candidates` flag on the strength of an
argument, not a measurement. Phase 3 measures it: run every scoring solver both
ways over the same seeded sample and report mean, worst case, and wall clock
for each. Unrestricted searches the full space every turn, so it is expected to
cost several times more time per game — the question is whether it buys enough
guesses back to be worth it, and for which strategy.

Whatever comes out, it gets written down. If unrestricted turns out to be no
better, that is the more interesting result and it goes in the README next to
the numbers that show it.

**Answered, partially.** Classic 3024 ruleset, 100 paired secrets, both sides
deterministic so the pairing is tight (correlations +0.49 to +0.78):

| Solver | Restricted | Unrestricted | Paired diff | 95% CI | Significant | Cost |
|---|---|---|---|---|---|---|
| entropy | 4.970 | 4.840 | +0.130 | [+0.010, +0.250] | yes | 5.3x slower |
| expected-size | 4.920 | 4.760 | +0.160 | [-0.034, +0.354] | no | 6.1x slower |
| minimax | 4.870 | 4.930 | -0.060 | [-0.224, +0.104] | no | 5.8x slower |

So the received wisdom holds for entropy and only just — the interval's lower
edge is +0.010. For expected-size it points the right way without clearing the
bar. For minimax the mean does not improve at all, though its sample maximum
falls from 7 to 6, which is the column it actually optimises and the one a
sample cannot settle.

Restricted stays the default: five to six times the runtime for a tenth of a
guess, on one solver of three, is not a trade worth making by default. Revisit
at n=300 and on a full sweep after Phase 5.

Add the information-theoretic floor to the writeup: with 3024 equally likely
secrets and 14 feedback outcomes, no strategy can average fewer than
log2(3024)/log2(14) guesses. Compute it, compare it to what the best solver
actually achieves, and explain the gap. That paragraph is worth more than the
rest of the README.

**Done when:** `make bench` regenerates every number and chart from scratch,
and the table is in the README.

---

## Phase 4 — CLI

`guesstimate/cli/`, using Rich.

- Mode A: computer guesses, you give feedback (the original game)
- Mode B: you guess, computer scores
- `--solver`, `--length`, `--alphabet`, `--repeats` flags
- After each turn in Mode A, show the surviving candidate count and a sparkline
  of the collapse so far
- Bad input never crashes; play-again loop; `--seed` for reproducible games

Record a terminal GIF for the README.

**Done when:** `uvx guesstimate` plays a full game.

---

## Phase 5 — Make it fast

Precompute the 3024x3024 feedback matrix as a `uint8` numpy array and cache it
to `data/`. Rewrite minimax, expected-size, and entropy to index the matrix
instead of recomputing scores every turn. Vectorize the partition counting.

Where it lives: `guesstimate/data/`, which is the layer permitted to do I/O —
the no-I/O rule binds `core/` and `solvers/` only. It builds lazily on first
use and caches to `data/feedback_matrix_<ruleset_hash>.npy`, gitignored and
regenerated by a `make matrix` target. The hash keys the cache to the ruleset,
so hex mode and length-6 mode get their own files instead of silently reusing
the wrong one. Solvers take the matrix as a constructor argument and never load
it themselves. Nothing builds at import time.

Then build the **opening book**: the optimal first guess is fixed, and there
are only 14 possible responses to it, so the best second guess for each is
precomputable. Ship it as JSON. The first two moves become instant lookups.

Profile before and after and record both numbers. Write a README section on it:
what the bottleneck was, why the matrix fixes it, what it costs in memory, and
what the opening book buys on top.

This is the section an interviewer will ask about. Every number must be one you
measured yourself.

### Named deliverable: test Knuth's claim properly

Phase 3 measured every solver over all 3024 secrets and found **restricted
minimax dominated** — worst case 7, identical to entropy and expected-size, and
a worse mean than either (5.044 against 5.008 and 5.011). It is paying for a
guarantee the other two get for free.

That is not yet a verdict on Knuth's method, because Knuth's guarantee comes
from *unrestricted* minimax: a solver allowed to play codes already ruled out,
on the grounds that a guess which cannot win may still split the survivors
better than any that can. Every full-sweep number so far is restricted. Over 100
sampled secrets, unrestricted minimax's sample maximum was 6 where restricted's
was 7 — one sample, but pointing at exactly the column the strategy exists to
improve.

The run that settles it is a full 3024-secret unrestricted sweep. At roughly
5.8x the cost of a restricted one that is about ten hours naively, which is why
it belongs here rather than in Phase 3: the matrix should make it affordable,
and if it does not, that is itself worth reporting.

Report worst case first, mean second, and put the answer next to the dominance
finding in `docs/notes/minimax-mean-vs-worst.md` whichever way it falls.

**Done when:** a full minimax benchmark runs in seconds, with before/after
timings committed, and unrestricted minimax has been swept over all 3024
secrets with its worst case published.

---

## Phase 6 — API and game server

`guesstimate/api/` on FastAPI. Thin routes over core and solvers — no game
logic in the route handlers.

```
POST /game                 start a game (mode, ruleset, solver, seed)
POST /game/{id}/guess      submit a guess, get feedback
POST /game/{id}/feedback   submit feedback to the solver, get its next guess
GET  /game/{id}/state      board, turn count, surviving count
GET  /game/{id}/candidates surviving candidate ids, for the visualization
GET  /game/{id}/analysis   post-game review data (Phase 8)
GET  /daily                today's seeded challenge
```

State server-side, keyed by session id, TTL'd. The secret never crosses the
wire until the game ends. Rate limit. OpenAPI docs come free — link them from
the README.

**Done when:** you can play a whole game with curl.

---

## Phase 7 — The web app

React + Vite + TypeScript + Tailwind. Read `DESIGN.md` before writing any
component. Four modes, specced in detail in `FEATURES.md`:

1. **Codebreaker** — you guess, the app scores
2. **Watch the solver** — the original game, visualized: all 3024 candidates
   rendered as a punch-card grid that gets knocked out as feedback narrows it
3. **Race the solver** — same secret, split screen, turn for turn
4. **Evil mode** — the adversarial codemaker that never commits to a number

The candidate-collapse animation in mode 2 is the signature of the whole
project. Budget real time for it. Everything else on the page stays quiet so
that one thing lands.

Quality floor, not negotiable: responsive to mobile, full keyboard play,
visible focus rings, `prefers-reduced-motion` respected, feedback conveyed by
shape and label as well as color.

**Done when:** all four modes work end to end on localhost.

---

## Phase 8 — Game review

The feature that makes people come back. Specced in `FEATURES.md` — after any
finished game, replay it turn by turn and show, for each guess the player made:

- how many candidates it actually eliminated
- how many the optimal guess would have eliminated
- the bits of information gained versus available
- a per-move rating, and one line explaining what the better guess was

Chess engine post-game analysis, for Bulls and Cows. As far as I can tell
nobody has built this.

**Done when:** finishing a game drops you into a scrollable review.

---

## Phase 9 — Shareability and the extras

- Daily challenge, seeded from the date, with a copyable emoji result grid
- LocalStorage stats: streak, guess distribution, win rate. No accounts.
- Difficulty settings exposed: length 3-8, hex mode, repeats toggle. A "zeros"
  toggle is just a swap between the `123456789` and `0123456789` alphabets —
  there is no separate flag for it
- Hint system with three tiers (see `FEATURES.md`)
- Puzzle mode: a fixed position, deduce the secret
- Live entropy HUD and the digit-position probability heatmap
- The "How it works" explainer page with interactive widgets
- Dynamic OG image so shared links preview the player's result grid

**Done when:** you can send someone the link with no explanation and they play.

---

## Phase 10 — The LLM evaluation

`guesstimate/eval/`. Have a language model play as codebreaker through the same
`Solver` protocol as everything else, and benchmark it against the four
algorithmic solvers over a sampled set of secrets.

Measure: mean guesses, worst case, and how often it makes an *inconsistent*
guess — one already ruled out by its own earlier feedback. That last metric is
the interesting one, because it isolates deductive bookkeeping from strategy.

Try a few prompting conditions: raw, chain-of-thought, and one where the model
is handed the surviving candidate count each turn. Chart all of them next to
minimax.

Whatever the result is, publish it honestly. A clean negative result is a
better writeup than a flattering one.

**Done when:** the LLM appears as another bar on the benchmark chart, with the
methodology written up.

---

## Phase 11 — Ship

- Compile the solver core to WebAssembly (Pyodide, or a Rust port) so the whole
  app can run client-side with no round trips and static hosting. Optional, but
  it makes the candidate animation instant and it is a real engineering flex.
- Deploy: API on Fly.io, frontend on Vercel. Real domain if you have one.
- README: demo GIF, live link, benchmark table, architecture diagram, the
  optimization writeup, the LLM eval, and one line about where the project came
  from. "Written in high school in 2021, rebuilt in 2026" is a better story
  than pretending it appeared fully formed.
- Coverage and CI badges. Open a handful of issues for things you deliberately
  did not build — a repo with a live issue tracker reads as maintained.

**Done when:** someone finds the repo, clicks one link, and is playing in under
ten seconds.

---

## What to skip

User accounts, a database, real-time multiplayer, server-persisted
leaderboards. Each adds infrastructure and none makes the project more
impressive. Daily challenge plus LocalStorage stats gets ~90% of the engagement
for none of the operational cost.

Mobile apps are **deferred, not skipped**. `MOBILE.md` specs a PWA foundation
and the two store builds as phases that start after Phase 9, and deliberately
does not number them here — nothing about them gets built until the web game is
finished. Two of its constraints do bind from Phase 1 onward, and they are
rules 9 and 10 in `CLAUDE.md`: keep the engine portable, and never let
server-authoritative state become the only way to play.
