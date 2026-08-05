"""Codes, and the only place a raw string is allowed to become one."""

from .ruleset import Ruleset

Code = tuple[str, ...]
"""A code is a tuple of single-character symbols.

Not a string, because indexing and slicing a string invites the off-by-one
crashes the original had. Not an int, because ints lose leading zeros and
cannot express a hex alphabet.
"""


def parse_code(text: str, ruleset: Ruleset) -> Code:
    """Turn user input into a `Code`, or raise.

    This is the boundary. Everything past it works on validated tuples, so no
    downstream function has to re-check length or symbols.

    Args:
        text: Raw input. Surrounding whitespace is ignored.
        ruleset: The rules the code has to satisfy.

    Returns:
        The parsed code.

    Raises:
        ValueError: If the text is the wrong length, uses a symbol outside the
            alphabet, or repeats a symbol when the ruleset forbids it.
    """
    stripped = text.strip()
    if len(stripped) != ruleset.length:
        raise ValueError(
            f"expected {ruleset.length} symbols, got {len(stripped)}: {text!r}"
        )

    code = tuple(stripped)
    for symbol in code:
        if symbol not in ruleset.alphabet:
            raise ValueError(
                f"symbol {symbol!r} is not in the alphabet {ruleset.alphabet!r}"
            )
    if not ruleset.allow_repeats and len(set(code)) != len(code):
        raise ValueError(f"this ruleset forbids repeated symbols: {text!r}")
    return code


def format_code(code: Code) -> str:
    """Render a code back to the string form `parse_code` accepts."""
    return "".join(code)
