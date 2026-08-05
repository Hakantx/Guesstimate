# CLAUDE.md

Rules for working in this repo. Read this first, every session.

Companion docs: `ROADMAP.md` (build order), `FEATURES.md` (feature specs),
`DESIGN.md` (visual direction), `MOBILE.md` (app store strategy). Read the
relevant one before starting a phase.

`MOBILE.md` describes work deferred until after Phase 9 — its phases are
deliberately absent from `ROADMAP.md` and nothing in it gets built yet. Two of
its constraints bind now anyway, and they are rules 9 and 10 below.

## What this is

Guesstimate is a Bulls and Cows solver, game, and research toy. The secret is a
4-digit number using digits 1-9, no zeros, no repeated digits — exactly
9x8x7x6 = 3024 possible secrets.

Feedback on a guess is written `+B-C`:
- B = digits correct and in the correct position
- C = digits present in the secret but in a different position

There are 14 distinct feedback outcomes, including the win. `+3-1` is
impossible — prove this to yourself before writing the scorer.

This started as a single 138-line Python script written in high school. It is
being rebuilt as a web app with four solver strategies, a benchmark suite, an
LLM evaluation harness, and a set of visualizations. The original is tagged
`v1.0-original` and stays in the history.

## Hard rules

1. **The core engine has no I/O.** Nothing in `guesstimate/core/` or
   `guesstimate/solvers/` may call `input()`, `print()`, touch the filesystem,
   or import anything web-related. Those layers are pure functions over data.
   Everything else depends on them; they depend on nothing.

2. **Every solver implements the same protocol.** One class, two methods:
   `guess()` returns the next guess, `update(guess, feedback)` narrows the
   candidate set. Adding a fifth strategy must not require touching the API,
   the UI, or any other solver.

3. **The engine is generic from day one.** Length, digit alphabet, repeats
   allowed — all parameters, never hardcoded. `Ruleset.alphabet` is the single
   source of truth for which symbols exist; there is no separate zeros flag,
   because zeros exist exactly when `"0"` is in the alphabet. Half the features
   in FEATURES.md are free if this is done right in Phase 1 and expensive
   retrofits if it isn't.

4. **Tests before implementation.** Write the failing test, then make it pass.
   The scoring function gets property-based tests with Hypothesis, not a
   handful of examples.

5. **One phase per branch, one concern per commit.** Do not jump ahead in
   ROADMAP.md because a later phase looks easy. Finish the current one, get it
   green in CI, merge.

6. **No new dependency without a stated reason.** If a stdlib solution exists
   and is under ~30 lines, use the stdlib.

7. **Explain, don't just produce.** For anything non-obvious — minimax
   selection, entropy calculation, the adversarial scorer, the matrix
   precompute — include a comment block explaining why it works, written so
   someone reading it cold understands. I need to be able to whiteboard every
   algorithm in this repo without looking at it.

8. **Never invent benchmark numbers.** Every figure that appears in the README
   comes from a run of `make bench` on this machine. If a number is not
   measured, it does not get written down.

9. **The engine gets ported to TypeScript, so write it portably.** `core/` and
   `solvers/` are ported later for on-device play (`MOBILE.md`), with a
   cross-language test asserting both implementations agree over the same
   seeded games. That port is a transcription, not a redesign, only if the
   Python stays small, dependency-free, and free of constructs with no TS
   equivalent: no metaclasses, no descriptors, no `__slots__` tricks, no
   operator-overloading cleverness, no dynamic attribute access, no reliance on
   generator laziness for correctness. Prefer plain functions over data,
   explicit loops over comprehension chains that only read well in Python, and
   stdlib types that map cleanly onto JS ones. `itertools` and `Counter` are
   fine — they are twenty lines of TypeScript each. numpy in `core/` is not,
   which is another reason the matrix lives in `data/`. This constrains the
   engine only; everything above it can be as Pythonic as it likes.

10. **Server-authoritative game state cannot be the only path.** Phase 6 keeps
    the secret server-side and that stays correct for the web. But the same
    game logic has to be able to sit behind a local in-process solver with no
    network at all, because offline play is what makes the mobile app more
    than a website in a shell. So define the game as an interface with two
    implementations — remote-backed and local — rather than as a set of HTTP
    routes with logic in them. Anything that assumes a round trip, a session
    id, or a server clock is a Phase 6 detail and does not belong in the
    shared layer.

## Stack

- Backend: Python 3.12, FastAPI, uv for dependency management
- Frontend: React + Vite + TypeScript + Tailwind, Framer Motion for the
  candidate-grid animation
- Tests: pytest, Hypothesis, vitest, Playwright for one end-to-end smoke test
- Lint/types: ruff, mypy (strict), eslint
- CI: GitHub Actions on every push — lint, types, tests, coverage, and a
  reduced benchmark that fails if mean guess count regresses

## Layout

```
guesstimate/
  core/          alphabet, candidates, scoring, feedback types. zero I/O.
  solvers/       one file per strategy + the shared protocol
  data/          feedback matrix + opening book: build, cache, load. does I/O.
  bench/         benchmark harness, result tables, chart generation
  eval/          LLM-as-player harness
  api/           FastAPI routes, thin wrappers over core + solvers
  cli/           terminal version
web/             React app
data/            precomputed feedback matrix, opening book (gitignored, built)
docs/            benchmarks, design notes, the how-it-works writeup
tests/
```

## Things that are easy to get wrong

- **Score by digit counts, not by pairwise comparison.** The pairwise
  double-loop happens to work when digits are unique and silently breaks the
  moment repeats are allowed. Count-based from the start:
  bulls = positions where they match; total common = sum over each symbol of
  min(count in secret, count in guess); cows = total common - bulls.

- **`+4-0` is the only winning feedback.** Never test for the win by looking at
  a single character of the string. Parse to a `Feedback` type at the boundary
  and compare values.

- **Validate at the boundary.** The original crashed on an empty line because
  it indexed a string before checking its length. Nothing past the parse layer
  should ever see a raw string.

- **Minimax is O(n^2) per turn if written naively.** Precompute the 3024x3024
  feedback matrix once as a uint8 numpy array (~9 MB) and index into it. Do
  this in Phase 5, not before — the naive version has to exist so the speedup
  can be measured honestly.

- **The matrix lives in `guesstimate/data/`, not in the solvers.** Rule 1's
  no-I/O ban covers `core/` and `solvers/` only; `data/` is the layer allowed
  to touch the filesystem. It builds the matrix lazily on first use, caches it
  to `data/feedback_matrix_<ruleset_hash>.npy` (gitignored, rebuilt by
  `make matrix`), and hands it back. Solvers receive the matrix as a
  constructor argument and never load it themselves — that keeps them pure,
  testable against a hand-built stub, and honest about their dependencies.
  Never build the matrix at import time: a 3024x3024 scoring pass on `import`
  makes the CLI, the test suite, and CI pay for something most of them never
  use.

- **Restricted vs unrestricted guessing.** Minimax and entropy can be limited
  to surviving candidates, or allowed to guess anything in the full space.
  Unrestricted is stronger. Implement both, make it a flag, benchmark both,
  and explain the tradeoff in a comment.

- **The adversarial codemaker must never contradict itself.** It picks the
  feedback that maximizes the surviving set, but that set has to stay
  consistent with every answer it already gave. If it can ever reach zero, the
  logic is wrong. Add a test that plays 1000 adversarial games and asserts the
  set is non-empty at every step.

- **Don't leak the secret to the browser.** Game state lives server-side, keyed
  by session id. In the client-side modes — WASM in Phase 11, the TypeScript
  solver port in `MOBILE.md` — the secret necessarily lives in the client, and
  the protection it buys is gone. That is an acceptable trade for offline play
  and a bad surprise if it happens by accident, so it must be a deliberate,
  documented mode switch and never the default for a hosted game.

## Style

- Type hints everywhere. mypy strict must pass.
- Docstrings on public functions; skip them on obvious private helpers.
- No commented-out code left in the tree.
- Commit messages: imperative mood, one line, no AI attribution footers.
