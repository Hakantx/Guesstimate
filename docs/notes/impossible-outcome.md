# Why `+3-1` cannot happen

In Bulls and Cows a guess is answered with two numbers: **bulls**, the symbols
that are correct and in the right position, and **cows**, the symbols that are
in the secret but somewhere else. The classic game uses four positions and the
digits 1-9 with no repeats, and the answer is written `+B-C` — so `+2-1` means
two placed, one misplaced.

Fifteen answers satisfy the obvious constraint that bulls plus cows cannot
exceed four. Only fourteen ever occur. The missing one is `+3-1`: three
correct positions and one misplaced digit. The usual explanation is a counting
argument specific to this ruleset — if three of the four digits are pinned,
the fourth has nowhere else to go, so it is either right or absent. That is
true, but it leans on digits being distinct, and it stops being obviously true
the moment you allow a secret like `1123`. The engine is generic over length,
alphabet, and whether repeats are allowed, so the interesting question is
whether the hole is a quirk of the classic rules or something structural.

It is structural, and the proof does not care about repeats. Suppose a guess
scores `length - 1` bulls: every position matches except one. Call the
secret's symbol at that odd position `s` and the guess's `g`; they must differ,
or that position would have been a bull too. Now count how many symbols the two
codes share, ignoring position — for any symbol `x`, the secret contains it
(however many times it was matched) plus one more if `x` is `s`, and the guess
contains it (the same matched count) plus one more if `x` is `g`. The shared
count is the smaller of those two, which only exceeds the matched count when
`x` is both `s` and `g` at once. Since `s` and `g` differ, that never happens,
so the total shared is exactly `length - 1`.

Cows are the shared symbols that are not bulls, so cows equals
`(length - 1) - (length - 1)`, which is zero. Being one bull short of a win
forces zero cows — for any code length, any alphabet, and whether or not
repeats are allowed. The classic game's fourteen outcomes are just this general
fact applied to a four-position triangle: fifteen pairs minus the one hole.
The practical consequence is that anything enumerating outcomes must exclude
`(length - 1, 1)` rather than assume a tidy triangle, and a scorer that ever
returns it has a bug.
