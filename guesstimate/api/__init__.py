"""FastAPI routes over the game interface.

Thin by construction: session ids, expiry, rate limits, and status codes live
here, and the rules of the game live in `guesstimate.game`, which the offline
build uses with no HTTP anywhere near it (CLAUDE.md rule 10).
"""

from .client import ModeNotSupportedError, RateLimitedError, RemoteGame
from .limits import RateLimiter
from .routes import app, create_app
from .sessions import Session, SessionStore

__all__ = [
    "ModeNotSupportedError",
    "RateLimitedError",
    "RateLimiter",
    "RemoteGame",
    "Session",
    "SessionStore",
    "app",
    "create_app",
]
