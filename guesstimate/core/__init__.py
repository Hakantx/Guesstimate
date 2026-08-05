"""The engine: rulesets, codes, scoring, and the candidate space.

Pure functions over data. Nothing here reads input, prints, touches the
filesystem, or imports anything web-related, and nothing here depends on any
other layer of the package.

It is also the layer that gets ported to TypeScript for on-device play, so it
stays small, dependency-free, and free of constructs that have no equivalent
there. See CLAUDE.md rules 1 and 9.
"""

from .candidates import all_candidates, feedback_space, filter_candidates
from .code import Code, format_code, parse_code
from .feedback import Feedback
from .ruleset import Ruleset
from .scoring import score

__all__ = [
    "Code",
    "Feedback",
    "Ruleset",
    "all_candidates",
    "feedback_space",
    "filter_candidates",
    "format_code",
    "parse_code",
    "score",
]
