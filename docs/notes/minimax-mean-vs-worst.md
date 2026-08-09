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

Everything above is this repo measuring itself. The stronger test is against
results from outside it, and for the standard variant of this game there are
two — one for each of the things a solver could be optimising:

- **Worst case.** Chen, Lin and Nguyen, *Strategy optimization for deductive
  games* (EJOR): 7 guesses are necessary and sufficient.
- **Expected length.** Tanaka (1996): the minimum achievable mean is **5.213**.

Both are stated for a different game from ours. Standard Bulls and Cows uses
the digits 0-9 with no repeats, which is 10 × 9 × 8 × 7 = **5040** secrets;
this project's default excludes zero, giving 9 × 8 × 7 × 6 = **3024**. A bound
proved for one says nothing directly about the other, so the honest move is to
play the variant the theorems are about rather than cite them beside numbers
from a different one.

Every secret in the 5040-code variant, same four solvers:

| Solver | Mean | vs 5.213 | Worst | vs 7 |
|---|---|---|---|---|
| entropy | 5.314 | +0.101 (+1.9%) | 8 | +1 (+14%) |
| expected-size | 5.319 | +0.106 (+2.0%) | 8 | +1 (+14%) |
| minimax | 5.354 | +0.141 (+2.7%) | 8 | +1 (+14%) |
| random | 5.458 | +0.245 (+4.7%) | 9 | +2 (+29%) |

## Greedy play is near-optimal on average and a full guess off at the tail

The two columns tell different stories, and the difference between them is the
most useful thing this project has measured.

On the mean, the best solver here is **within 2%** of a bound proved to be
unbeatable. That is close. Playing greedily — picking whatever guess looks best
this turn, never once considering the position it leaves behind — costs about a
tenth of a guess per game against a strategy computed by searching whole game
trees.

On the worst case, the same solver needs **a full extra guess**, 8 where 7 is
provably enough, a 14% overshoot. And every strategy here overshoots by exactly
one, including the strategy whose entire purpose is the worst case.

That shape is what local optimisation predicts. A greedy choice is a small
mistake most of the time: it takes the guess that splits the current candidate
set best, which is usually also a fine guess for the game as a whole, and when
it is slightly wrong the cost is a fraction of a turn on that one branch.
Averaged over five thousand games those fractions stay small, which is why the
mean lands within 2%.

The worst case does not average anything. It is the single deepest branch, and
that branch is reached by a run of positions where the locally best guess is
not the globally best one — each choice individually defensible, the
accumulation fatal. Greedy mistakes rarely matter on average precisely because
they are rare; the tail is where the rare things all happened at once, and it is
exactly where compounding shows up. Optimal play buys a locally worse guess now
to avoid a bad split two turns later, which is what the paper's title means by
*strategy optimization*, and it is a fundamentally more expensive computation
than anything in this repo.

One caveat on reading the two bounds together: they optimise different
objectives, and the strategy attaining one is not generally the strategy
attaining the other. 5.213 and 7 are two separate targets, not a single
scoreboard some known policy hits simultaneously.

## The information floor is not the bar

This is also a useful correction to a number this project has been publishing
since Phase 3. The information-theoretic floor for the 5040 variant --
log2(5040)/log2(14), assuming every guess splits the space perfectly evenly --
is **3.230** guesses. The achievable optimum is 5.213.

So the floor understates the real target by more than 60%. It is a true lower
bound and a nearly useless one, because no single code splits 5040 candidates
into fourteen equal parts, let alone does so repeatedly. Quoting a solver's
distance from the floor makes it look far worse than it is: entropy is 2.08
guesses above the floor and 0.10 above what is actually attainable. Both
numbers belong in the table, and only the second one is a measure of how well
the solver plays.

### A tighter floor that does not work

The obvious repair is to replace the theoretical cap with a measured one. No
guess actually extracts log2(14) = 3.807 bits on the opening, because no code
splits 5040 candidates evenly; the best first guess extracts **2.771** bits.
Substituting that gives log2(5040)/2.771 = **4.438**, which closes 62% of the
distance to the achievable 5.213 and looks like a much better bound.

It is not a bound at all. The substitution is only valid if no guess anywhere in
the game extracts more than the best opening guess does, and that is false. The
reason the opening extracts so little is that 5040 candidates cannot be carved
evenly into fourteen groups — but thirty candidates often can be, and a guess
that splits thirty survivors into fourteen near-equal groups extracts close to
the full 3.807 bits.

Measured over 149 mid-game positions from real games: **101 of them offered more
information than the best opening guess**, by up to 0.68 bits. Information per
guess goes *up* as the candidate set shrinks, not down. A floor built on the
first-turn maximum is therefore not conservative, and the fact that 4.438 still
happens to sit below 5.213 is luck rather than validity.

What survives is the weaker claim. Entropy of a partition into at most `k`
blocks is at most log2(k) at every stage of every game, so log2(N)/log2(k) is
sound, and it is sound precisely because it does not try to use anything about
a particular position. Getting a genuinely tighter bound needs a different
argument — one that accounts for the endgame, where the candidate set is small,
the information available per guess is nearly irrelevant, and what actually
costs turns is that the last guess has to name the code exactly.

## What to take from it

The honest summary has three parts, and the variant has to be attached to each.

On the 3024-code default, minimax's worst case is matched by both other
strategies while its mean is worse than both, so there is no column in which it
wins. Whether 7 is optimal for that variant is unknown here; no published bound
covers it.

On the 5040-code standard variant, where both optima are known, every greedy
strategy lands within 2% of the optimal mean and one full guess above the
optimal worst case. The worst-case guarantee minimax offers is real — much
better than the random baseline's 9 — but it is neither exclusive nor optimal,
and it is not what separates the strategies from each other.

And the practical consequence for the benchmark tables: worst case and mean
both have to be reported, because a mean-only table makes minimax look strictly
inferior and a worst-case-only table makes it look equal, and the interesting
fact is that it is simultaneously both. A table that also states its variant is
the minimum needed for any of it to be checkable.

<sub>Guess counts above are exact over every secret. The 5040 sweep's wall-clock
timings are not published: it ran alongside another sweep on a two-core machine
and its timings are contended. Counts are unaffected by that.</sub>
