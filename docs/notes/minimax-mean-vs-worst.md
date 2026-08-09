# What minimax buys, and what it does not

Four strategies play Bulls and Cows here. The baseline picks at random from the
codes still consistent with everything it has been told. The other three each
look at every guess available, work out how the still-possible secrets would be
split up by the answer, and judge that split — minimax by its largest group,
expected-size by its average group, entropy by the information it reveals.

Minimax is the one with a story attached. It assumes the answer will be the
least helpful one available and plays to make that worst case as good as
possible, which sounds like it should own the worst-case column outright. Over
a full sweep of every secret, it does not.

## On our ruleset, the guarantee is real but not exclusive

Every secret in the default 3024-code game — four positions, digits 1-9, no
repeats — played by all four solvers:

| Solver | Mean | Worst |
|---|---|---|
| entropy | 5.008 | 7 |
| expected-size | 5.011 | 7 |
| minimax | 5.044 | 7 |
| random | 5.161 | 9 |

Minimax reaches a worst case of 7 and so does everything else that thinks. The
strategy built to optimise the worst case attains the same worst case as two
strategies that are not trying to, and pays for it with the worst mean of the
three.

Allowing it to guess codes already ruled out — the setting where a worst-case
argument is usually made, since a guess that cannot win may still split the
survivors better than any that can — does not rescue it:

| Minimax | Mean | Worst |
|---|---|---|
| restricted | 5.044 | 7 |
| unrestricted | 5.063 | 7 |

The worst case does not move and the mean gets slightly worse. Unrestricted
play does help the other two on the mean — expected-size improves 5.011 to
4.970 and entropy 5.008 to 4.962 — so the extra freedom is worth something, but
not to the strategy that most wanted it.

An earlier sample suggested otherwise: over 100 of the 3024 secrets,
unrestricted minimax's maximum was 6 against restricted's 7. That was the
sampling artefact this project already warns about in its own tables. A maximum
drawn from 3% of a space is a lower bound on the real one, and that run simply
never drew a secret that costs 7.

## The external check, and the more interesting result

Everything above is this repo measuring itself. The stronger test is against a
result from outside it, and one exists: Chen, Lin and Nguyen, *Strategy
optimization for deductive games* (EJOR), prove that **7 guesses are necessary
and sufficient in the worst case** for Bulls and Cows.

That theorem is stated for a different game from ours. The standard Bulls and
Cows uses the digits 0-9 with no repeats, which is 10 × 9 × 8 × 7 = **5040**
secrets. This project's default excludes zero, giving 9 × 8 × 7 × 6 = **3024**.
Those are different games, and a bound proved for one says nothing directly
about the other — so the honest move is to play the variant the theorem is
about rather than to cite it next to numbers from a different one.

Every secret in the 5040-code variant, same four solvers:

| Solver | Mean | Worst | Proven optimum |
|---|---|---|---|
| entropy | 5.314 | **8** | 7 |
| expected-size | 5.319 | **8** | 7 |
| minimax | 5.354 | **8** | 7 |
| random | 5.458 | 9 | 7 |

**None of them attain the bound.** Every strategy here, including the one whose
entire purpose is the worst case, needs 8 guesses on the hardest secrets where
7 is provably enough.

The gap is not a bug, it is the difference between two kinds of play. All four
solvers are *greedy*: each turn they pick the guess that looks best for that
turn, and never consider what position it leaves them in afterwards. The proven
bound comes from optimising the whole strategy — searching over game trees for
a policy that keeps every branch inside seven guesses, which can mean playing a
locally worse guess now to avoid a bad split two turns later. That is what the
paper's title means by *strategy optimization*, and it is a different and far
more expensive computation than anything in this repo.

So the measurement that was meant to validate the solvers instead measures
something better: **one full guess separates greedy play from optimal play on
this game**, and it separates them for all three strategies equally. Minimax's
worst-case focus buys nothing that the other two do not already get, and does
not close the gap to optimal either.

## What to take from it

The honest summary has three parts, and the variant has to be attached to each.

On the 3024-code default, minimax's worst case is matched by both other
strategies while its mean is worse than both, so there is no column in which it
wins. Whether 7 is optimal for that variant is unknown here; no published bound
covers it.

On the 5040-code standard variant, where the optimum is known to be 7, every
greedy strategy lands on 8. The worst-case guarantee minimax offers is real —
it is much better than the random baseline's 9 — but it is neither exclusive
nor optimal.

And the practical consequence for the benchmark tables: worst case and mean
both have to be reported, because a mean-only table makes minimax look strictly
inferior and a worst-case-only table makes it look equal, and the interesting
fact is that it is simultaneously both. A table that also states its variant is
the minimum needed for any of it to be checkable.

<sub>Guess counts above are exact over every secret. The 5040 sweep's wall-clock
timings are not published: it ran alongside another sweep on a two-core machine
and its timings are contended. Counts are unaffected by that.</sub>
