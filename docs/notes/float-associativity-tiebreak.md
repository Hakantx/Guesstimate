# Two correct implementations, one divergent game

The fast version of this project's solver reads answers out of a precomputed
table instead of working them out. It is meant to be an optimisation and
nothing else: same strategy, same choices, same games, less time. Checking that
turned up something better than a speedup.

## The setup

A solver's inner question is what a guess would do to the set of codes still
possible. Any guess splits that set into groups — one group per answer the
guess could draw — and a strategy judges the guess by the shape of the split.
The entropy strategy judges it by information: a split into many small groups
tells you more than a split into one big one, and it computes how much using
Shannon's formula, summing one term per group.

There are two ways to produce those group sizes. The straightforward one walks
the candidates, scores each against the guess, and tallies the answers in a
counter, which reports groups in the order it first met them. The table-backed
one looks up a whole row at once and counts occurrences of each answer, which
reports groups in the order the answers are numbered.

Both are correct. They produce the same groups with the same sizes. They differ
only in what order they hand them over, and nothing about the mathematics cares
about order: entropy is a sum, and addition is commutative.

## The divergent game

Playing the 60-code ruleset with the secret `245`, both solvers open with `123`
and are told `+0-1`. Twelve candidates survive. Then they disagree. One plays
`345`, the other plays `245`. Both go on to win; one takes a turn longer.

The disagreement is over a single guess's score. Guess `245` splits those twelve
survivors into groups of 1, 2, 1, 4, 3, 1 as the counter met them, and into 4,
1, 3, 2, 1, 1 as the table numbers them. Same six groups. The entropy of that
split, computed by adding the same six terms in those two orders:

```
counted order   [1, 2, 1, 4, 3, 1]   ->  -2.3553885422075336
table order     [4, 1, 3, 2, 1, 1]   ->  -2.355388542207534
```

They differ by 4.44e-16, about two units in the last place of a double. The true
entropy is a single number and neither result is it; both are that number
rounded, slightly differently.

Addition is commutative but floating-point addition is **not associative**.
Every intermediate sum gets rounded to the nearest representable double, and
what gets rounded away depends on what has already accumulated. Add the same
numbers in a different order and the rounding errors land in different places.

That would be harmless if the number were only ever displayed. It is not — it
is compared. At this position several guesses are genuinely tied, all splitting
the survivors equally well, and the solver breaks ties by a deliberate rule:
prefer a guess that could itself win, then take the earliest in alphabet order.
That rule never runs, because two guesses that are mathematically tied are not
tied in floating point. Two ULPs is enough to make one strictly smaller than
the other, so the ranking is decided by rounding noise before the tie-break has
a chance to speak.

This is not a rare alignment. Scanning part of the same small ruleset found 550
positions where the two orderings disagree on a cost.

Only entropy is affected, and the reason is worth noting: minimax scores a
split by its largest group, and `max` does not care about order; expected-size
sums squared group sizes, which are integers, and integer addition *is*
associative. Entropy is the only one of the three that accumulates floats, so
it is the only one where the order of the groups reaches the answer.

## Why every outcome-based test passed

The solver suite at that point was thorough. It checked that every solver wins
from every secret, that the candidate set never loses the true code, that the
set shrinks every turn, that guesses come from the declared pool, that the
strategies beat a random baseline, and that identical seeds reproduce identical
results. All of it passed, on both implementations, throughout.

None of it could have caught this. Every one of those properties is about
*outcomes* — did it win, in how many guesses, was the answer right. Both
solvers won every game. The full benchmark means were unchanged to three
decimal places, because the two solvers were not better or worse than each
other, just different. A test that samples results and compares statistics sees
two identical solvers, because statistically that is what they are.

What catches it is comparing the games themselves. The equivalence test records
the entire sequence of guesses from both implementations and asserts the
sequences are equal, turn by turn, rather than asserting the final answers
match. That is a strictly stronger claim and it failed on the first run, naming
the secret and the turn where the two parted company.

The general lesson is about what an optimisation is allowed to be. "Produces
the same answers" is the wrong bar, because a solver that plays differently and
wins anyway produces the same answers. The right bar is "makes the same
decisions", and only a transcript can show that. Anything weaker leaves a
reordering free to change behaviour silently, and reordering is exactly what
optimisations do.

## The fix is a contract, not a patch

The instinct is to make the two implementations agree — have the table-backed
one enumerate groups the way the counter does. That would work and it would be
fragile: it makes one implementation's incidental iteration order into a
specification the other has to reverse-engineer, and the next implementation
has to rediscover it.

Instead the interface now states the guarantee. Group sizes are returned in
ascending order, by every implementation, and the docstring explains that this
is not cosmetic — that a float cost summed in two orders can differ in the last
bit, and that the difference is enough to flip a tie. The property being
protected is that a strategy's choice depends on the *multiset* of group sizes
and on nothing else. Sorting is how a multiset is turned into a canonical
sequence, so sorting is where the guarantee belongs.

It also puts the fix where a future implementation cannot miss it. A third
partitioner — a WebAssembly one, or the TypeScript port — inherits the
requirement from the interface rather than having to notice the problem
independently.

## Sorting ascending is also the better summation order

There is a well-known rule of thumb that a sum of positive numbers is more
accurate computed smallest-first: while the running total is small, the
additions are between operands of comparable size, and fewer low-order bits get
rounded away than when a small term is added to an already-large accumulator.

That rule does not obviously apply here. It assumes the terms being summed are
sorted, and what gets sorted is the group *sizes* — while the term contributed
by a group is not monotonic in its size. A group holding a fraction `p` of the
candidates contributes `-p·log₂p`, which rises, peaks around `p = 1/e`, and
falls back to zero as `p` approaches one. Sorting sizes ascending does not sort
the terms ascending, so the usual argument is not available and the question
has to be settled by measurement.

Measured over 20,000 randomly generated partitions, against a correctly rounded
reference:

| Order | Mean absolute error | Matches the correctly rounded value |
|---|---|---|
| ascending | 1.356e-16 | 67.9% |
| as counted | 1.546e-16 | 64.4% |
| descending | 1.800e-16 | 59.9% |

Ascending wins: about 25% less error than descending and 12% less than
arbitrary order, and it lands on the correctly rounded result eight times in
ten more often than descending does. The margin is modest, and the reason for
sorting remains determinism rather than accuracy — but of the orders available,
the one required for correctness also happens to be the most accurate, which is
a pleasant thing not to have to trade away.
