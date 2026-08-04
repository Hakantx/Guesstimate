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
guess anything in the full space, including numbers already ruled out — which
is sometimes stronger, because a guess that cannot possibly win can still split
the remaining set better than any that can.

Write minimax naively. It will be slow. That is deliberate; Phase 5 measures
the speedup.

Tie-breaking matters and must be deterministic: prefer a guess that is itself
still a candidate, then lowest lexicographic order. Document it, or benchmarks
won't reproduce.

**Done when:** all four solve any secret, and a test asserts none exceeds a
guess ceiling across a sampled sweep of secrets.

---

## Phase 3 — Benchmark suite

`guesstimate/bench/` runs every solver against all 3024 secrets and reports:

- mean, median, worst case, and standard deviation of guess count
- the full distribution as a histogram
- wall-clock time per game and per turn
- how many candidates survive after guess 1, 2, 3 (the collapse curve)

Emit a markdown table plus matplotlib charts into `docs/benchmarks/`. Wire it
to `make bench`. Seed every random source so runs reproduce.

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

Then build the **opening book**: the optimal first guess is fixed, and there
are only 14 possible responses to it, so the best second guess for each is
precomputable. Ship it as JSON. The first two moves become instant lookups.

Profile before and after and record both numbers. Write a README section on it:
what the bottleneck was, why the matrix fixes it, what it costs in memory, and
what the opening book buys on top.

This is the section an interviewer will ask about. Every number must be one you
measured yourself.

**Done when:** a full minimax benchmark runs in seconds, with before/after
timings committed.

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
- Difficulty settings exposed: length 3-8, hex mode, repeats and zeros toggles
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
leaderboards, native mobile apps. Each adds infrastructure and none makes the
project more impressive. Daily challenge plus LocalStorage stats gets ~90% of
the engagement for none of the operational cost.
