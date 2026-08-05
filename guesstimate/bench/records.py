"""One row per game, appended as it finishes so a run can be resumed."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .provenance import Provenance


@dataclass(frozen=True)
class GameRecord:
    """What one finished game contributes to the tables.

    `secret_index` is the position in the sample, not in the candidate space.
    It is what pairs a result across solvers: every solver plays index 3
    against the same secret, so their guess counts can be differenced directly.
    """

    config: str
    secret_index: int
    secret: str
    guesses: int
    seconds: float
    turn_seconds: tuple[float, ...]
    survivors: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        """Render for a JSONL row."""
        return {
            "config": self.config,
            "secret_index": self.secret_index,
            "secret": self.secret,
            "guesses": self.guesses,
            "seconds": self.seconds,
            "turn_seconds": list(self.turn_seconds),
            "survivors": list(self.survivors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GameRecord:
        """Rebuild from a JSONL row."""
        return cls(
            config=data["config"],
            secret_index=data["secret_index"],
            secret=data["secret"],
            guesses=data["guesses"],
            seconds=data["seconds"],
            turn_seconds=tuple(data["turn_seconds"]),
            survivors=tuple(data["survivors"]),
        )


class RecordStore:
    """Append-only JSONL of finished games, with the run's provenance on line 1.

    Resumability is the point. A full sweep is hours, and a machine that sleeps
    or a terminal that closes should cost the games still outstanding rather
    than all of them. Each game is flushed as it completes, so the file is
    always a valid partial run.

    Reopening checks the stored provenance against the one handed in and
    refuses to continue if they differ. Without that, resuming after changing
    the seed or the commit would silently blend two runs into one table, which
    is worse than losing the work -- the resulting numbers would look fine.
    """

    def __init__(self, path: Path, provenance: Provenance) -> None:
        self.path = path
        self.provenance = provenance
        self._records: list[GameRecord] = []

        if path.exists():
            self._load()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as handle:
                handle.write(json.dumps({"provenance": provenance.to_dict()}) + "\n")

    def _load(self) -> None:
        with self.path.open(encoding="utf-8") as handle:
            header = json.loads(handle.readline())
            stored = Provenance.from_dict(header["provenance"])
            if stored.fingerprint() != self.provenance.fingerprint():
                raise ValueError(
                    f"{self.path} holds a different run -- same file, different "
                    f"commit, machine, ruleset, sample size or seed. Delete it "
                    f"to start fresh rather than mixing two runs into one table."
                )
            self.provenance = stored
            for line in handle:
                if line.strip():
                    self._records.append(GameRecord.from_dict(json.loads(line)))

    def append(self, record: GameRecord) -> None:
        """Write one finished game, flushing so a kill loses nothing before it."""
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict()) + "\n")
        self._records.append(record)

    def records(self) -> list[GameRecord]:
        """Every game recorded so far, in the order it was written."""
        return list(self._records)

    def done(self, config: str) -> set[int]:
        """Sample indices already played for a config."""
        return {r.secret_index for r in self._records if r.config == config}
