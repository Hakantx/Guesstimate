"""Shared Hypothesis strategies.

Property tests enumerate the whole candidate space, so the rulesets they draw
have to stay small. Everything here is bounded by `max_space` and drawn without
`assume()`, so no test wastes examples on rejections.
"""

from hypothesis import strategies as st

from guesstimate.core import Code, Ruleset, all_candidates

# Deliberately mixes digits and hex letters: the engine must never assume its
# symbols are numeric.
ALPHABET_POOL = "123456789ABCDEF"

DEFAULT_MAX_SPACE = 400


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
    symbols = draw(
        st.lists(st.sampled_from(ALPHABET_POOL), min_size=1, max_size=6, unique=True)
    )
    alphabet = "".join(sorted(symbols))
    allow_repeats = draw(st.booleans())
    length = draw(
        st.integers(
            min_value=1, max_value=_max_length(alphabet, allow_repeats, max_space)
        )
    )
    return Ruleset(length=length, alphabet=alphabet, allow_repeats=allow_repeats)


@st.composite
def rulesets_with_code(draw: st.DrawFn) -> tuple[Ruleset, Code]:
    ruleset = draw(rulesets())
    return ruleset, draw(st.sampled_from(all_candidates(ruleset)))


@st.composite
def rulesets_with_two_codes(draw: st.DrawFn) -> tuple[Ruleset, Code, Code]:
    ruleset = draw(rulesets())
    candidates = all_candidates(ruleset)
    secret = draw(st.sampled_from(candidates))
    guess = draw(st.sampled_from(candidates))
    return ruleset, secret, guess
