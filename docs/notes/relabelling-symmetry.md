# Counting the reachable outcomes, and why the obvious formula is wrong

The engine needs to know every answer a given ruleset can produce. That list is
not cosmetic: solvers group candidates by outcome, and the planned feedback
matrix stores an outcome as a one-byte index into it, so the list has to be
exact and stably ordered.

The tempting shortcut is arithmetic. Bulls plus cows cannot exceed the code
length, one outcome is impossible (see `impossible-outcome.md`), so the answer
looks like "every pair in the triangle, minus one." For the classic game that
gives the correct fourteen, which is exactly the sort of agreement that stops
you looking further. It is wrong in general, and a small case shows it: a
two-symbol alphabet with repeats allowed and length four. Getting zero bulls
there means the guess disagrees at every position, which over two symbols means
it is the exact complement of the secret. If the secret has `k` copies of the
first symbol, the complement has `4 - k`, and the shared count works out to
twice the smaller of the two — always even. So `+0-3` is unreachable, even
though it sits comfortably inside the triangle. Which outcomes a ruleset can
actually produce depends on the alphabet, not just the length, so the function
has to measure rather than assume.

Measuring naively means scoring every secret against every guess: 3024 × 3024
for the classic game, nine million scorings for a fourteen-item answer. The way
out is a symmetry. Scoring only ever asks whether two symbols are *equal*, never
which symbol they are, so renaming symbols cannot change any score — if you
apply a permutation of the alphabet to both the secret and the guess, the answer
is identical. Rearranged, that means scoring a renamed secret against some guess
equals scoring the original secret against the correspondingly renamed guess.
And as the guess ranges over the whole space, so does its renamed version. So a
secret and any renaming of it reach exactly the same set of outcomes.

That collapses the work to one secret per renaming class. A code is the
representative of its class when each symbol's first appearance is the earliest
unused alphabet symbol — `1123` represents the "one symbol twice, then two new
ones" pattern, and `2231` is the same pattern under different names. When
repeats are off, every code is the same pattern of all-distinct symbols, so
there is exactly **one** class and the classic game costs 3024 scorings instead
of nine million. With repeats on, the count is the number of ways to partition
the positions into at most `len(alphabet)` groups — 15 for length 4, 41 for
length 5 over three symbols — which is a smaller but still large saving.

The testing lesson turned out to be sharper than the optimization. Checking the
shortcut against full brute force catches it dropping classes, which would
silently return too few outcomes. It cannot catch the filter being switched off
entirely, because scoring every secret produces the *right* answer, just far
more slowly — for a while the only thing failing on that mutation was a timing
deadline. A correctness optimization needs a correctness test, so the suite now
also asserts the exact class counts (1, 15, 41) by value. Those numbers are the
combinatorics the optimization rests on, so the test doubles as documentation
of why it is allowed to work.
