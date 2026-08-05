"""The `+B-C` answer to a guess."""

from __future__ import annotations

from dataclasses import dataclass

_DIGITS = "0123456789"


@dataclass(frozen=True)
class Feedback:
    """Bulls and cows: how close a guess was.

    Bulls are symbols that are correct and in the right position. Cows are
    symbols present in the secret but somewhere else. The pair is the *entire*
    result of a turn -- which positions were bulls is never revealed.

    Frozen and hashable because solvers group candidates into a dict keyed by
    feedback. When that gets ported to TypeScript, `str(feedback)` is the
    canonical key form.

    Attributes:
        bulls: Correct symbol, correct position.
        cows: Correct symbol, wrong position.
    """

    bulls: int
    cows: int

    def __post_init__(self) -> None:
        """Reject counts that cannot come out of a scorer."""
        if self.bulls < 0 or self.cows < 0:
            raise ValueError(
                f"feedback counts cannot be negative: {self.bulls}, {self.cows}"
            )

    def __str__(self) -> str:
        return f"+{self.bulls}-{self.cows}"

    @classmethod
    def parse(cls, text: str) -> Feedback:
        """Parse the `+B-C` form, or raise.

        Args:
            text: Raw input. Surrounding whitespace is ignored.

        Returns:
            The parsed feedback.

        Raises:
            ValueError: If the text is not exactly `+<digits>-<digits>`.
        """
        stripped = text.strip()
        separator = stripped.find("-")
        if not stripped.startswith("+") or separator < 0:
            raise ValueError(f"feedback must look like +2-1, got {text!r}")

        bulls, cows = stripped[1:separator], stripped[separator + 1 :]
        # int() would happily take "+2", " 2", and unicode digits. Feedback is
        # compared for equality all over the engine, so only one spelling of a
        # given outcome is allowed to parse.
        for part in (bulls, cows):
            if not part or any(character not in _DIGITS for character in part):
                raise ValueError(f"feedback must look like +2-1, got {text!r}")
        return cls(bulls=int(bulls), cows=int(cows))

    def is_win(self, length: int) -> bool:
        """Whether this feedback ends the game under a code length of `length`.

        Every position is a bull and nothing is left over. Ask this instead of
        looking at a character of the rendered string, and never compare against
        a hardcoded `+4-0` -- the length is a ruleset parameter.
        """
        return self.bulls == length
