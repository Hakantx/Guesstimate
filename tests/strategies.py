"""Shared Hypothesis strategies.

Two scales, because one is not enough:

`rulesets()` draws small variants -- odd alphabets, repeats on and off, lengths
that do not divide neatly -- to hunt for structural mistakes. Properties over
these enumerate the whole candidate space, so the spaces have to stay small, and
everything is drawn without `assume()` so no example is wasted on a rejection.

`classic_codes()` draws from the real 3024-candidate game. The bounded strategy
above can never reach it, and a property that holds for a 6-candidate toy but
not for the game the project is actually about would be worth nothing.
"""

from hypothesis import strategies as st

from guesstimate.core import Code, Feedback, Ruleset, all_candidates, feedback_space

# Deliberately mixes digits and hex letters: the engine must never assume its
# symbols are numeric.
ALPHABET_POOL = "123456789ABCDEF"

# Properties over these rulesets enumerate the candidate space, sometimes once
# per outcome, so the budget trades example quality against suite runtime. It
# also sets how interesting the games are: a small budget forces small alphabets,
# small alphabets cap the length, and length-1 games make most properties
# vacuous. Measured over 1500 draws, raising 400 to 1000 took the share of
# length-1 rulesets from 47% to 37% and doubled the mean space to 99 codes, for
# about a second of suite time.
DEFAULT_MAX_SPACE = 1000

# `feedback_space` scores one representative secret per relabelling class, and
# with repeats allowed the number of classes grows fast -- length 6 over a
# 3-symbol alphabet has 122 of them, so the call costs 122 x 729 scores and
# blows Hypothesis's 200ms deadline. Tests that call it per example get a
# smaller budget instead of a disabled deadline, so a genuine slowdown in the
# engine still shows up as a failure.
SPACE_HEAVY_MAX_SPACE = 300

CLASSIC = Ruleset()
_CLASSIC_CANDIDATES = all_candidates(CLASSIC)


def _max_length(alphabet: str, allow_repeats: bool, max_space: int) -> int:
    hard_cap = len(alphabet) if not allow_repeats else 6
    best = 1
    for length in range(1, hard_cap + 1):
        if Ruleset(length, alphabet, allow_repeats).space_size <= max_space:
            best = length
        else:
            break
    return best


@st.composite
def rulesets(draw: st.DrawFn, max_space: int = DEFAULT_MAX_SPACE) -> Ruleset:
    """A small game variant: any alphabet, any length that fits, repeats either way."""
    symbols = draw(
        st.lists(st.sampled_from(ALPHABET_POOL), min_size=1, max_size=6, unique=True)
    )
    alphabet = "".join(sorted(symbols))
    allow_repeats = draw(st.booleans())
    # A flat draw over the whole range. Note this does not buy much on its own:
    # what actually caps the length is the alphabet, since two symbols with no
    # repeats can only make a length-2 code. The share of length-1 rulesets is
    # governed by `max_space`, not by how this line draws.
    length = draw(
        st.sampled_from(range(1, _max_length(alphabet, allow_repeats, max_space) + 1))
    )
    return Ruleset(length=length, alphabet=alphabet, allow_repeats=allow_repeats)


def codes(ruleset: Ruleset) -> st.SearchStrategy[Code]:
    """Any code the ruleset allows, drawn uniformly from the whole space."""
    return st.sampled_from(all_candidates(ruleset))


def classic_codes() -> st.SearchStrategy[Code]:
    """Any of the 3024 codes of the real game: length 4, digits 1-9, no repeats."""
    return st.sampled_from(_CLASSIC_CANDIDATES)


def feedbacks() -> st.SearchStrategy[Feedback]:
    """Any well-formed feedback, reachable or not.

    Deliberately unconstrained: counts run past any sane code length so the
    `+B-C` format is tested beyond single digits.
    """
    return st.builds(Feedback, bulls=st.integers(0, 50), cows=st.integers(0, 50))


@st.composite
def rulesets_with_code(draw: st.DrawFn) -> tuple[Ruleset, Code]:
    ruleset = draw(rulesets())
    return ruleset, draw(codes(ruleset))


@st.composite
def rulesets_with_two_codes(draw: st.DrawFn) -> tuple[Ruleset, Code, Code]:
    ruleset = draw(rulesets())
    return ruleset, draw(codes(ruleset)), draw(codes(ruleset))


@st.composite
def rulesets_with_reachable_feedback(draw: st.DrawFn) -> tuple[Ruleset, Feedback]:
    """A ruleset paired with an outcome that ruleset can actually produce."""
    ruleset = draw(rulesets(max_space=SPACE_HEAVY_MAX_SPACE))
    return ruleset, draw(st.sampled_from(feedback_space(ruleset)))
