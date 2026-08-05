"""The rules of a game: how long a code is and which symbols it may use."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Ruleset:
    """A game variant.

    The classic game is the default: four positions, the digits 1-9, no repeats.
    Everything else in the engine reads its parameters from here and hardcodes
    nothing, so hex mode, longer codes, and repeats-allowed all come free.

    There is deliberately no `allow_zeros` flag. Zeros exist exactly when "0" is
    in the alphabet, and adding a second way to say the same thing invites the
    two to disagree.

    Attributes:
        length: How many positions a code has.
        alphabet: The symbols a code may use, each exactly one character.
            Candidate order follows this order, so keep it sorted unless you
            want the grid in DESIGN.md laid out some other way.
        allow_repeats: Whether a symbol may appear more than once in a code.
    """

    length: int = 4
    alphabet: str = "123456789"
    allow_repeats: bool = False

    def __post_init__(self) -> None:
        """Reject rulesets that describe no possible code."""
        if self.length < 1:
            raise ValueError(f"length must be at least 1, got {self.length}")
        if not self.alphabet:
            raise ValueError("alphabet must contain at least one symbol")
        if len(set(self.alphabet)) != len(self.alphabet):
            raise ValueError(f"alphabet has duplicate symbols: {self.alphabet!r}")
        if any(symbol.isspace() for symbol in self.alphabet):
            raise ValueError(f"alphabet must not contain whitespace: {self.alphabet!r}")
        if not self.allow_repeats and self.length > len(self.alphabet):
            raise ValueError(
                f"length {self.length} needs {self.length} distinct symbols, but the "
                f"alphabet has {len(self.alphabet)} and repeats are off"
            )

    @property
    def space_size(self) -> int:
        """How many codes exist under these rules, without enumerating them.

        With repeats every position is an independent choice, so the count is
        `len(alphabet) ** length`. Without repeats each position consumes a
        symbol, giving the falling factorial `A * (A-1) * ... * (A-length+1)` --
        9 * 8 * 7 * 6 = 3024 for the classic game.

        Written as a loop rather than `math.perm` and `**` because neither has a
        TypeScript equivalent that returns an exact integer, and this way the
        port is a transcription (CLAUDE.md rule 9).
        """
        symbols = len(self.alphabet)
        size = 1
        for taken in range(self.length):
            # With repeats every position may use any symbol. Without, each
            # position consumes one, so the pool shrinks as we go.
            size *= symbols if self.allow_repeats else symbols - taken
        return size
