"""What a set of numbers has to carry with it to mean anything later."""

from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from guesstimate.core import Ruleset


def _tree_is_dirty(output_dir: Path | None) -> bool:
    """Whether anything outside the run's own output differs from the commit."""
    status = _git("status", "--porcelain")
    if not status:
        return False

    ignored = None
    if output_dir is not None:
        root = _git("rev-parse", "--show-toplevel")
        try:
            ignored = output_dir.resolve().relative_to(Path(root).resolve())
        except (ValueError, OSError):
            ignored = None

    for line in status.splitlines():
        path = line[3:].strip().strip('"')
        if ignored is not None and Path(path) == ignored:
            continue
        if ignored is not None and str(ignored) in path:
            continue
        return True
    return False


def _git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, check=True, timeout=10
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return ""


@dataclass(frozen=True)
class Provenance:
    """Everything needed to reproduce a benchmark run, or to distrust it.

    A mean guess count with no sample size beside it is not a result, and a
    table that cannot be traced back to a commit is not evidence of anything
    six weeks later. Rule 8 says published figures come from `make bench` --
    that is only checkable if each table says which run produced it.

    `git_dirty` asks whether the *code* differs from the commit, ignoring the
    benchmark's own output directory. Without that exclusion the flag is
    useless: the harness writes its results into the tree, so every run would
    report itself dirty on account of the files it had just written, and a
    genuinely uncommitted solver change would look exactly the same.

    One limit remains: two dirty trees at the same commit are indistinguishable
    here, so a resumed run can span an edit. The flag marks the numbers as not
    corresponding to anything another person can check out, which is the
    important part.
    """

    git_sha: str
    git_dirty: bool
    python: str
    machine: str
    processor: str
    cpu_count: int
    ruleset: dict[str, Any]
    sample_size: int
    seed: int
    started_utc: str

    @classmethod
    def capture(
        cls,
        ruleset: Ruleset,
        sample_size: int,
        seed: int,
        output_dir: Path | None = None,
    ) -> Provenance:
        """Read the current machine, checkout, and run parameters.

        `output_dir` is where this run will write. Changes under it are not
        counted as a dirty tree -- they are the run's own results, not a code
        difference that would stop someone reproducing the numbers.
        """
        return cls(
            git_sha=_git("rev-parse", "HEAD") or "unknown",
            git_dirty=_tree_is_dirty(output_dir),
            python=f"{platform.python_implementation()} {platform.python_version()}",
            machine=platform.platform(),
            processor=platform.processor() or "unknown",
            cpu_count=os.cpu_count() or 1,
            ruleset={
                "length": ruleset.length,
                "alphabet": ruleset.alphabet,
                "allow_repeats": ruleset.allow_repeats,
                "space_size": ruleset.space_size,
            },
            sample_size=sample_size,
            seed=seed,
            started_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        )

    def fingerprint(self) -> tuple[Any, ...]:
        """The parts that must match for two runs to be the same run.

        Deliberately excludes `started_utc`: resuming is meant to continue a
        run on a later day. Everything else is included, because mixing results
        from two commits, two machines, or two seeds into one table produces a
        number that describes nothing.
        """
        return (
            self.git_sha,
            self.git_dirty,
            self.python,
            self.machine,
            tuple(sorted(self.ruleset.items())),
            self.sample_size,
            self.seed,
        )

    def to_dict(self) -> dict[str, Any]:
        """Render for the JSONL header."""
        return {
            "git_sha": self.git_sha,
            "git_dirty": self.git_dirty,
            "python": self.python,
            "machine": self.machine,
            "processor": self.processor,
            "cpu_count": self.cpu_count,
            "ruleset": self.ruleset,
            "sample_size": self.sample_size,
            "seed": self.seed,
            "started_utc": self.started_utc,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Provenance:
        """Rebuild from a JSONL header."""
        return cls(**data)

    def to_markdown(self) -> str:
        """A block to sit above every published table."""
        ruleset = self.ruleset
        shape = (
            f"length {ruleset['length']}, alphabet `{ruleset['alphabet']}`, "
            f"repeats {'on' if ruleset['allow_repeats'] else 'off'} "
            f"({ruleset['space_size']} codes)"
        )
        dirty = " (tree dirty)" if self.git_dirty else ""
        return "\n".join(
            [
                "| Provenance | |",
                "|---|---|",
                f"| Commit | `{self.git_sha[:12]}`{dirty} |",
                f"| Ruleset | {shape} |",
                f"| Sample | {self.sample_size} secrets |",
                f"| Seed | {self.seed} |",
                f"| Machine | {self.machine} |",
                f"| Processor | {self.processor}, {self.cpu_count} cores |",
                f"| Python | {self.python} |",
                f"| Run started | {self.started_utc} |",
            ]
        )
