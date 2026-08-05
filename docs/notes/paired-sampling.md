# Pairing helps between strategies, and not at all against the random baseline

Comparing two solvers means comparing two averages, and averages of noisy
things need a lot of samples before a small difference is believable. The
standard fix is pairing: run both solvers on the *same* secrets rather than on
two independent samples, then look at the per-secret difference. If a secret is
intrinsically hard, it costs both solvers extra, and differencing removes that
shared difficulty entirely. What is left is the effect you actually care about,
measured against a much smaller spread.

That reasoning is correct and it is why this project's benchmark draws one
seeded sample and gives it to every configuration. Measured on the classic
3024-code game over 100 paired secrets, it works exactly as advertised —
between the strategies. Expected-size and minimax agree closely on which
secrets are hard (correlation +0.83), so differencing them gives a spread of
0.61 where treating them as independent would imply 1.49. Entropy against
expected-size is +0.71 and 0.76 against 1.41. Pairing cuts the variance by
around two and a half times, which is the difference between needing 200
secrets and needing 1,300.

Against the random baseline it does nothing whatsoever. The correlation between
the random solver's guess count and any strategy's, across the same secrets, is
between −0.13 and −0.06 — statistically indistinguishable from none. The paired
spread comes out at 1.34 to 1.48, which is what you would get by treating the
two runs as unrelated samples. Pairing recovered no variance at all because
there was no shared component to recover.

The reason is that the random solver's result is not really a measurement of
the secret. It picks uniformly from whatever candidates survive, so its path
through a game is dominated by its own coin flips rather than by anything
intrinsic to the code it is hunting. One secret that takes a strategy five
guesses might take the baseline three or seven depending only on which
survivors it happened to draw. There is no per-secret difficulty term shared
with the strategies, so differencing cancels nothing and simply adds the two
variances together.

Two practical consequences. First, solver-versus-solver comparisons in this
repo are trustworthy at far smaller samples than solver-versus-baseline ones,
and the tables should not imply otherwise — a footnote claiming "paired
sampling, so these are tight" is true of one half of the table and false of the
other. Second, the fix for the baseline is to stop treating a single random
game as its score for a secret: run the baseline over several seeds per secret
and average, which shrinks its per-secret noise and restores something for the
pairing to cancel. That is a change to the harness rather than to the analysis,
and it is not yet made.

The measured effects against the baseline at n=100 were +0.25 guesses for
minimax, +0.20 for expected-size, and +0.15 for entropy, none of them clearing
a 95% interval. The sample sizes those effects would need are 135, 198, and 305
respectively — which is a decent post-hoc justification for the harness
defaulting to 300, and a reminder that the smallest of the three gaps is still
out of reach at that size.
