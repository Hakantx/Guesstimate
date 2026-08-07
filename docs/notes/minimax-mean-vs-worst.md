# Minimax loses to guessing at random, and that is not a bug

Four strategies play Bulls and Cows here. The baseline picks at random from the
codes still consistent with everything it has been told. Minimax, the strategy
Knuth published for Mastermind in 1977, does something far more deliberate: for
every guess it could make, it works out how the still-possible secrets would be
split up by the answer, and picks the guess whose largest resulting group is
smallest.

Measured over every secret in a 120-code ruleset, minimax averaged 3.933
guesses. The random baseline averaged between 3.908 and 3.983 depending on its
seed. So on a good seed, random beats the strategy that thinks. That looks like
a bug and is not one — it is minimax doing exactly what it was asked.

Widen the ruleset to 360 codes and the ordering flips back: minimax averages
4.083 against a baseline of 4.119 to 4.136, and now it wins. That reversal is
the actual finding. Minimax is not *reliably* worse than random on the mean;
it is *indifferent* to the mean, so where it lands relative to a naive baseline
is a property of the ruleset rather than of the strategy. A single measurement
in either direction would have been easy to over-read.

The reason is in what minimax optimises. It assumes the answer will be the
least helpful one available, and plays to make that worst case as good as
possible. It never asks how likely the worst case is. A guess that usually
splits the possibilities beautifully but occasionally leaves a big awkward
group will lose to a guess that always leaves a medium group, because minimax
compares only those two largest groups. Averaged over many games, "always
medium" can easily be worse than "usually excellent, rarely bad" — but minimax
has no way to express that, because averages are not what it is looking at.
Whether that costs it anything depends on how often the trade comes up in a
given ruleset, which is why the answer moved between 120 and 360 codes. The
strategies that do optimise the average, expected-size and entropy, beat random
on every seed at both sizes.

What minimax buys instead is a guarantee. Its worst case is bounded in a way
nothing else here is: on a 60-code ruleset it never needed more than 4 guesses,
while random needed 5. That is the trade, and it is the same trade as the
difference between a fast average commute and one that is never late. Which you
want depends on whether you are being graded on the typical game or the ugliest
one.

## Measured over every secret: minimax is dominated

The argument above says minimax trades mean for worst case. That trade is only
worth making if the worst case actually improves, and a sampled run cannot say
whether it does — a maximum is not estimable from 100 of 3024 secrets. The full
sweep can, and it is not kind to minimax.

Every one of the 3024 secrets, played by all four solvers:

| Solver | Mean | Worst | 6-guess games | 7-guess games |
|---|---|---|---|---|
| entropy | 5.008 | 7 | 781 | 32 |
| expected-size | 5.011 | 7 | 791 | 31 |
| minimax | 5.044 | 7 | 852 | 37 |
| random | 5.161 | 9 | 4517* | 844* |

<sub>Classic 4/1-9 ruleset, every secret, seed 20260805. Random is over 15,120
games — 3024 secrets at five seeds each — so its counts are marked.</sub>

**Minimax is dominated on this ruleset.** Its worst case is 7, exactly the same
as entropy's and expected-size's, and its mean is worse than both. It is not
buying the guarantee it costs a fifth of a guess to obtain, because the other
two strategies already reach the same bound without aiming at it. The tail is
worse too, not just the average: minimax needs 7 guesses on 37 secrets against
entropy's 32, and 6 on 852 against 781. There is no column in this table where
it wins.

What the strategies do buy is visible against the baseline. Random reaches 9
guesses and needs 7 or more on 874 of its games; every strategy caps at 7. So
thinking helps, and thinking specifically about the worst case does not help
more than thinking about information.

## The measurement this does not make

One thing is missing before this counts as a verdict on Knuth's method rather
than on this implementation of it. Knuth's five-guess guarantee comes from
*unrestricted* minimax — a solver free to play any code in the space, including
ones already ruled out, precisely because such a guess can split the survivors
better than any that could win. The runs above are all restricted, and a
restricted minimax is a weaker thing than the one the guarantee describes.

There is already a hint that it matters: over 100 sampled secrets, unrestricted
minimax's sample maximum was 6 where restricted's was 7. That is one sample and
proves nothing, but it points the right way, and it is exactly the column the
strategy exists to improve. Settling it needs a full 3024-secret unrestricted
sweep, which at roughly 5.8x the cost of a restricted one is about ten hours on
the reference machine — so it waits for the Phase 5 matrix, and is named as a
deliverable there.

Until that runs, the honest statement is narrow: *restricted* minimax is
dominated on the classic ruleset, and the claim it was built to demonstrate has
not yet been tested.


Two practical consequences. First, any benchmark table has to report worst case
alongside the mean, because a mean-only table makes minimax look strictly
inferior and a worst-case-only table makes it look strictly superior, and
neither is true. Second, a test asserting "the clever solvers beat the random
one on mean guesses" is a wrong test for minimax specifically — it was written
that way here at first, and it would have quietly encoded a false claim about
what the strategy is for. The suite now asserts the mean comparison only for
entropy and expected-size, with minimax's absence explained where it would
otherwise look like an oversight.
