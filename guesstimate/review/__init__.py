"""Post-game analysis: what each guess was worth where it was played.

Pure, like the engine and the solvers -- it reads a finished game and returns
numbers. The API and the web app render those; nothing here knows they exist.
"""

from .game import MoveReview, review_game
from .grades import BANDS, Grade, grade_for
from .metrics import Best, best_at, bits_gained, expected_remaining

__all__ = [
    "BANDS",
    "Best",
    "Grade",
    "MoveReview",
    "best_at",
    "bits_gained",
    "expected_remaining",
    "grade_for",
    "review_game",
]
