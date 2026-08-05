# A test that only failed when it was being measured

Hypothesis, the property-testing library this project uses, generates many
inputs per test and applies a per-example wall-clock **deadline** — 200ms by
default. Exceed it and the example fails. The intent is to catch a function
that has quietly become pathological on some input, which is a reasonable thing
to want.

Several tests here enumerate an entire candidate space per example, so they sit
in the tens of milliseconds rather than the microseconds a typical property test
takes. That was fine until the suite was run under coverage. Coverage
instrumentation traces every executed line, which costs roughly two to three
times the runtime, and that was enough to push some examples past 200ms. The
result was a test that failed under `pytest --cov`, passed under plain
`pytest`, and passed again on an immediate re-run of the identical command. CI
runs with coverage, so it had been passing on luck rather than on correctness —
the failure surfaced locally only because the suite happened to get slower for
an unrelated reason.

The reflex fix is to disable the deadline, and here that reflex was wrong at
first. The deadline was, at that moment, the *only* thing catching a specific
regression: switching off an optimization in the outcome-enumerating code
produces an identical answer far more slowly, so every value-based assertion
still passed and only the clock noticed. Disabling it then would have removed
real coverage and left nothing behind. The right order was to replace the
timing signal with a value-based one — assert the exact size of the shortcut,
not how long it takes — and only then drop the deadline on the tests whose
runtime is inherently variable.

Two things generalise. First, a timing threshold inside a correctness test is
not really a test of correctness; it is a performance test wearing a
correctness test's name, and it will drift with hardware, instrumentation, and
CI load. Reference hardware here is a slow 2017 dual-core laptop, so anything
tuned to a fast machine would have failed anyway. Second, a flaky failure is
worth more attention than the two minutes it takes to re-run and move on. This
one was pointing at a genuine hole: an optimization with no correctness test
behind it. The flake was the symptom, not the problem.
