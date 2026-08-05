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

The reason is in what minimax optimises. It assumes the answer will be the
least helpful one available, and plays to make that worst case as good as
possible. It never asks how likely the worst case is. A guess that usually
splits the possibilities beautifully but occasionally leaves a big awkward
group will lose to a guess that always leaves a medium group, because minimax
compares only those two largest groups. Averaged over many games, "always
medium" is worse than "usually excellent, rarely bad" — but minimax has no way
to express that, because averages are not what it is looking at. The strategies
that do look at averages, expected-size and entropy, came in at 3.883, ahead of
random on every seed.

What minimax buys instead is a guarantee. Its worst case is bounded in a way
nothing else here is: on a 60-code ruleset it never needed more than 4 guesses,
while random needed 5. That is the trade, and it is the same trade as the
difference between a fast average commute and one that is never late. Which you
want depends on whether you are being graded on the typical game or the ugliest
one.

Two practical consequences. First, any benchmark table has to report worst case
alongside the mean, because a mean-only table makes minimax look strictly
inferior and a worst-case-only table makes it look strictly superior, and
neither is true. Second, a test asserting "the clever solvers beat the random
one on mean guesses" is a wrong test for minimax specifically — it was written
that way here at first, and it would have quietly encoded a false claim about
what the strategy is for. The suite now asserts the mean comparison only for
entropy and expected-size, with minimax's absence explained where it would
otherwise look like an oversight.
