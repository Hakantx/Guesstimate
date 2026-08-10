# The request body was choosing how much memory to allocate

Guesstimate is generic over its rules. Length, alphabet, and whether digits may
repeat are all parameters, which is what lets the same engine play the classic
4-digit game, a hex variant, or anything else. When the HTTP API arrived, those
parameters became fields in a request body, and a client got to choose them.

Starting a game enumerates every code the rules allow, because that is the set
of candidates a solver narrows down. For the default game that is 3,024 codes
and about a megabyte. The enumeration is a single line and it had been correct
and unremarkable for five phases.

```
POST /game  {"ruleset": {"length": 8, "alphabet": "0123456789ABCDEF"}}
```

Sixteen symbols in eight positions with no repeats is 518,918,400 codes. As
tuples of characters that is roughly **62 GB**, allocated eagerly, by one
unauthenticated request costing the sender nothing. The process does not
return an error. It dies.

## How it was found

Not by looking for it. The roadmap said the API should be rate limited, and
while writing a token bucket the question came up of what a rate limit is
actually protecting — which invites the question of what a single request can
cost. One request costing 62 GB makes a per-minute request cap beside the
point.

The bug had been reachable since the first route existed and every test passed
throughout, because every test asked for a sensible ruleset. Nothing was
fuzzing the parameters, and no reviewer looks at `all_candidates(ruleset)` and
sees an allocation sized by a stranger — it reads as domain logic, which is
exactly what it is.

The general shape is worth naming: **a parameter that was safe for five phases
became dangerous the moment an untrusted caller could set it.** Nothing about
the enumeration changed. What changed was who chooses its argument. Any value
that flows from a request body into a size — a limit, a count, a dimension, a
loop bound, a buffer — deserves looking at again the first time it crosses that
line, and generic code is where this hides, because being parameterised is the
whole point of it.

## The obvious fix was half a fix

The immediate repair is a cap: refuse rulesets whose candidate space exceeds
some number of codes. That was set at 100,000 — comfortably above anything the
app offers, comfortably below anything that hurts. It closes the hole it was
aimed at, and memory stops being reachable from the request body.

It also leaves a second hole that is harder to see, because it fixes the wrong
resource. Allocating the candidate list is linear. *Choosing a guess* is not:
a scoring solver compares every guess it might make against every candidate
still standing, which is quadratic, and it does that every turn.

At the cap, that is 100,000 squared — ten billion pairs. Measured on the
reference machine at about 7 microseconds a pair, the opening move alone takes
**roughly twenty hours of CPU**, from one request, well inside a 100,000-code
limit chosen to be safe. The memory hole became a slow-request hole, which is
worse in one respect: nothing crashes, so nothing alerts, and the worker is
simply gone.

The gap was almost invisible because both limits are expressed in the same unit.
"How many codes may a game have" sounds like one question. It is two, and they
have different answers by three orders of magnitude.

## What the cap had to become

Cost, not size — and per solver, because the four differ enormously:

| Mode / solver | Work per turn | What bounds it |
|---|---|---|
| codebreaker (no solver) | linear | memory |
| `RandomSolver` | linear | memory |
| minimax, expected-size, entropy | quadratic | CPU |

So the check estimates the seconds the opening move will take and refuses
anything over a per-request budget of about a second. The estimate uses the
calibration the benchmark harness already needed: a measured cost per scored
pair, and a measured cost per pair scanned through the precomputed matrix. Those
differ by roughly three hundred times, so *which* implementation will serve the
request changes the answer completely, and the estimate has to know.

The result respects the difference rather than flattening it. The random solver
is allowed the full 43,680-code hex ruleset because linear work on that space is
free. Entropy is refused it, with a message naming the estimated cost and
suggesting a smaller ruleset, the random solver, or codebreaker mode. A single
number would have had to be low enough for entropy, and would then have banned
random from spaces it handles comfortably.

## The consequence worth stating

Because the estimate counts a matrix build when no cached matrix exists, a
freshly deployed server refuses the larger rulesets for solver-backed modes
until its matrices are warm. That is deliberate — building one inside a request
is exactly the expensive work being bounded — but it makes `make matrix` a
deployment step rather than a developer convenience, and a cold server is
therefore more restrictive than a warm one.

Stating it here because it is the kind of thing that otherwise gets discovered
by a user, on the day of a deploy, as an unexplained refusal.
