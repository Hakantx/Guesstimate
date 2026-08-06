# A finding that did not survive being tested properly

Two rulesets were measured and they told a tidy story. On the classic Bulls and
Cows game — four positions, digits 1-9, no repeats — a strategy that computes
the information value of every possible guess beat guessing at random among
consistent candidates by 0.15 guesses, with a confidence interval running from
−0.11 to +0.41. That interval straddles zero, so the difference was not
significant, and it got read as an absence: strategy does not matter here. On a
smaller ruleset with repeated symbols the same comparison produced a clear,
significant gap. The obvious conclusion was that the classic game collapses too
fast for cleverness to pay, and that strategy only starts to matter when each
guess carries less information.

That conclusion was wrong, and the way it was wrong is worth keeping.

The two rulesets differed on every axis at once — alphabet size, code length,
number of candidates, number of distinct feedback outcomes, whether repeats were
allowed. Any of those could have explained the difference, including none of
them. So five rulesets were measured instead, chosen to hold the number of
candidates roughly fixed near a thousand to three thousand while trading
alphabet size against length: four symbols over five positions, ten symbols over
three, and three arrangements in between. Three hundred paired secrets each,
same protocol throughout.

Every one of the five showed a significant lead for the strategy, the classic
game included. Its lead came out at +0.143 with an interval of +0.036 to +0.250
— the same effect as before, measured with enough precision to see it. The
effect had not changed. The measurement had gone from a hundred secrets to three
hundred, and the random baseline had gone from a single game per secret to the
average of five, which cut its noise substantially. Nothing about the classic
game was special; the earlier result had been a wide interval wearing the
costume of a discovery.

The grid also failed to find what it was looking for. Correlations between the
size of the lead and each candidate explanation were weak — around −0.55 for
alphabet size, −0.57 for the number of candidates, +0.43 for the number of
feedback outcomes — and with five data points, none of that means anything;
you would need something past ±0.88 before it was worth a second look. The
sharper point is that every pair of confidence intervals overlaps. The leads
span 0.115 guesses across all five rulesets while a single estimate is worth
give or take 0.108, so there is no demonstrated difference between any two of
them. Separating these would need many more secrets per ruleset, or many more
rulesets strung out along one axis with the others genuinely held still.

## What this grid does not cover

Only one strategy was measured — the entropy solver — against the random
baseline. Minimax and expected-size are unmeasured on four of these five
rulesets, and minimax is the interesting omission, since it optimises the worst
case rather than the mean and could plausibly behave differently as the shape
of the ruleset changes.

Running them is deliberately *not* the next step. Three solvers across five
rulesets produces fifteen overlapping intervals rather than five, and the
limiting factor here is the number of rulesets, not the number of solvers —
adding solvers buys no power to separate the axes the grid was built to
separate. The useful version of this experiment is more rulesets strung along
a single axis with the others genuinely held still, at which point running all
three solvers over it costs little extra and answers something.

Two things to carry forward. A non-significant result is a wide interval, not a
zero — the discipline is to report the interval and stop, rather than to
convert it into a claim about the world that happens to be more interesting than
"we could not tell". And a comparison between two conditions that differ in five
ways cannot attribute the difference to any one of them, however plausible the
story. The fix for both is the same and it is not subtle: more points, one axis
at a time, and intervals on everything.
