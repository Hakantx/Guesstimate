# Guesstimate — Feature Specs

Detailed specs for everything in `ROADMAP.md`. Build order lives there; what
each thing actually does lives here.

Features are marked **core** (the project is incomplete without it),
**signature** (the reason someone remembers this repo), or **stretch**.

---

## 1. Codebreaker — you guess *(core)*

The ordinary game. You have a board of turns; you enter a code; the app returns
bulls and cows.

- Digit entry by keyboard or by an on-screen keypad. Digits already eliminated
  by your own feedback are dimmed on the keypad, not disabled — you can still
  play them, but you can see you shouldn't.
- Invalid guesses rejected inline, at the input, with the reason. Never a modal,
  never an alert.
- Feedback rendered as markers, not as the string `+2-1`. Filled marker for a
  bull, hollow for a cow. Shape and position carry the meaning so the game is
  playable without color.
- Turn counter, and an unobtrusive "possibilities remaining" readout that you
  can toggle off if you want to play blind.

---

## 2. Watch the solver *(signature)*

Your original game — the computer guesses, you give feedback — turned into the
thing people screenshot.

All 3024 candidates are rendered as a dense grid of small tiles, laid out like
a punch card: 63 columns by 48 rows, ordered by each candidate's index in the
sorted permutation list. Every tile is one possible secret. Leading digits fall
into contiguous horizontal bands as a consequence of the sort order, not as a
layout rule — see `DESIGN.md`.

Each turn:

1. The solver guesses. The guess is highlighted in the grid.
2. You enter feedback.
3. Every candidate inconsistent with that feedback is knocked out — a stagger
   animation, not a single frame flip, so you can watch the shape of the
   elimination sweep across the grid.
4. The surviving count ticks down. 3024 → ~250 → ~30 → ~4 → 1.

Extras that cost little and add a lot:

- A solver picker that can be changed mid-game. Watching entropy carve the grid
  differently than random does is the whole pitch.
- A speed control, including step-by-step.
- The collapse curve plotted underneath as a small sparkline.
- Hovering a surviving tile shows why it's still alive: which of your feedbacks
  it's consistent with.

Respect `prefers-reduced-motion` by cross-fading instead of staggering.

---

## 3. Race the solver *(core)*

Same secret, split screen. You on the left, the chosen solver on the right,
turn for turn. Neither side sees the other's guesses until both have played the
turn, then both boards reveal simultaneously.

You will lose. That's the point — losing to minimax by two turns is what makes
someone click "how does this work."

---

## 4. Evil mode *(signature)*

The computer never picks a number.

It holds the full candidate set and, for each guess you make, partitions the
set by what feedback each candidate would produce. Then it answers with
whichever feedback leaves the largest partition alive, and keeps only that
partition. It never contradicts itself — every answer it has ever given remains
true of every surviving candidate — so you can't catch it cheating. It just
drags you out as long as the mathematics allows.

UI: play it straight. Don't announce anything. Show the surviving count, which
falls much more slowly than the player expects. At the end, reveal that no
secret was ever chosen and show how many candidates were still standing when
you finally cornered it.

Test it hard: 1000 automated games asserting the surviving set is non-empty at
every step and consistent with every answer given.

---

## 5. Game review *(signature)*

The best idea in this document. Chess post-game analysis, for a deduction game.

After any finished game, replay it turn by turn. For each guess the player made:

| Shown | Meaning |
|---|---|
| Candidates before / after | how much the guess actually narrowed the field |
| Best possible after | what the optimal guess would have left |
| Efficiency | actual reduction as a fraction of the best available |
| Bits gained / available | the same thing in information-theoretic terms |
| Verdict | one of: optimal, solid, loose, wasted |

A "wasted" verdict is a guess that was already ruled out by the player's own
prior feedback — the most common real mistake, and one people don't notice
themselves making.

Each move gets one line of plain-language explanation: what the better guess
was and roughly why it splits the field more evenly. Write these as templated
sentences from real numbers, not as freeform generated text.

Close with an overall game rating and the player's biggest single miss.

---

## 6. Hint system *(core)*

Three tiers, each costing something so it stays a real decision:

1. **Count** — how many candidates are still alive.
2. **Heatmap** — a 9x4 grid showing, across all surviving candidates, the
   probability that each digit sits in each position. This is genuinely
   beautiful as it sharpens over a game, and it teaches the player what
   deduction feels like.
3. **The move** — what minimax would play from here, and the size of the worst
   case it guarantees.

Hints are disabled in daily challenge mode, or flagged on the shared result.

---

## 7. Entropy HUD *(stretch, high value)*

A meter showing information remaining. Starts at log2(3024) ≈ 11.6 bits and
drains toward zero as you narrow the field. Each guess reports the bits it
actually gained against the maximum it could have.

Pair it with the fact that there are only 14 possible feedback outcomes, so a
single guess can carry at most log2(14) ≈ 3.8 bits. That immediately explains
why nobody solves this in two turns, and it's the hook for the explainer page.

---

## 8. Daily challenge *(core)*

One secret per day, derived deterministically from the date so everyone in the
world gets the same one. No login. Solve it once.

Result grid in emoji, copyable — bulls, cows, and misses as three glyphs, one
row per guess, with the date and turn count. Choose glyphs that read correctly
in monochrome.

Dynamic OG image so a shared link previews the actual result grid.

---

## 9. Puzzle mode *(stretch)*

Not a game — a position. You're handed three or four guesses with their
feedback and asked to name the secret. Exactly one answer is consistent.

Generate these by playing random games and stopping at the turn where the
surviving set reaches exactly one. Rate difficulty by how many candidates
survived the second-to-last turn: a puzzle that goes 40 → 1 is much harder than
one that goes 3 → 1.

This mode is the one that works well as a daily thing on mobile and needs no
animation at all.

---

## 10. Rulesets *(core, nearly free)*

If Phase 1 was built generically, all of this is a settings panel:

- Length 3 through 8
- Repeated digits allowed or not
- Zeros: not a setting of its own. `Ruleset.alphabet` is the single source of
  truth for which symbols exist, so the UI's zeros toggle swaps the alphabet
  between `123456789` and `0123456789` and nothing else changes
- **Hex mode**: alphabet `0-9A-F`. Length 4 hex with repeats is 65,536
  candidates — enough to make the solver visibly work for it and enough to
  break naive minimax, which is a good demonstration of why Phase 5 matters.
- **Letters mode**: a 5-letter alphabet code. This is Wordle's mechanic with
  the numbers game's feedback, and the identical engine handles it.

Show the candidate count for the chosen ruleset in the settings panel, live.
Watching it jump from 3024 to 65,536 as you flip a toggle teaches combinatorics
faster than a paragraph would.

---

## 11. Solver comparison page *(core)*

The benchmark output, rendered in the app rather than buried in the README:

- Guess-count distributions for all four solvers, overlaid
- The collapse curve: mean candidates remaining after each turn, per solver
- Time per turn, before and after the Phase 5 optimization
- The information-theoretic floor drawn as a line, with the gap called out

Every number pulled from the generated benchmark JSON. Nothing typed by hand.

---

## 12. LLM as a player *(signature, and the most current thing here)*

Wire a language model into the same `Solver` protocol as everything else and
benchmark it head to head with minimax.

Each turn the model receives the ruleset, the full history of guesses and
feedback, and is asked for its next guess. Nothing else — no candidate list, no
hints.

Metrics:

- Mean and worst-case guesses versus the algorithmic solvers
- **Consistency rate**: how often it guesses something already eliminated by
  feedback it has been given. This is the interesting number, because it
  separates deductive bookkeeping from strategic choice.
- How performance degrades as the ruleset gets larger (4 digits → 6 digits →
  hex)

Conditions worth testing: plain, with reasoning enabled, and one where the
model is told how many candidates remain each turn.

Cache every response so reruns are free and the results reproduce. Publish the
result whatever it is. A clean negative is a better writeup than a flattering
one, and "I built an eval harness for deductive reasoning" is a stronger
sentence than "I made a game."

---

## 13. How it works *(stretch, high value for a portfolio)*

An explainer page, written for someone who has never heard of information
theory:

- Why 3024, derived rather than stated
- Why there are 14 feedback outcomes and why `+3-1` is impossible
- What "consistent candidate" means, with a widget where you enter feedback and
  watch the set shrink
- What minimax optimizes versus what entropy optimizes, and why they usually
  agree
- Why the theoretical floor is where it is, and why real solvers land above it

Being able to explain your own project clearly is worth as much as building it.

---

## 14. Two-player duel *(stretch)*

Same secret, no accounts, no server state. Encode the seed in a URL. Your friend
opens the link, plays the same secret, and the result screen compares turn
counts. Everything lives in the URL and LocalStorage.

---

## Deliberately not building

Accounts, a database, real-time multiplayer, server-side leaderboards, native
apps, an in-app tutorial carousel. Each adds infrastructure or friction, and
none of them makes the project better.
