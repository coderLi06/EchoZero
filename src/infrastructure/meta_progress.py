"""Tiny local-only meta progression for repeated procedural runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class MetaProgress:
    completed_runs: int = 0
    failed_runs: int = 0
    veteran_frame_unlocked: bool = False
    last_seed: int | None = None

    @property
    def starting_core_bonus(self) -> int:
        return 1 if self.veteran_frame_unlocked else 0

    def record_result(self, victory: bool) -> bool:
        was_unlocked = self.veteran_frame_unlocked
        if victory:
            self.completed_runs += 1
        else:
            self.failed_runs += 1
        if self.completed_runs + self.failed_runs >= 1:
            self.veteran_frame_unlocked = True
        return self.veteran_frame_unlocked and not was_unlocked


def load_meta_progress(path: Path) -> MetaProgress:
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return MetaProgress()
    except (OSError, UnicodeError, json.JSONDecodeError):
        return MetaProgress()
    if not isinstance(raw, dict):
        return MetaProgress()
    completed = raw.get("completed_runs", 0)
    failed = raw.get("failed_runs", 0)
    unlocked = raw.get("veteran_frame_unlocked", False)
    if (
        isinstance(completed, bool)
        or not isinstance(completed, int)
        or completed < 0
        or isinstance(failed, bool)
        or not isinstance(failed, int)
        or failed < 0
        or not isinstance(unlocked, bool)
    ):
        return MetaProgress()
    last_seed = raw.get("last_seed")
    if (
        last_seed is not None
        and (isinstance(last_seed, bool) or not isinstance(last_seed, int))
    ):
        last_seed = None
    return MetaProgress(completed, failed, unlocked, last_seed)


def save_meta_progress(path: Path, progress: MetaProgress) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "completed_runs": progress.completed_runs,
        "failed_runs": progress.failed_runs,
        "veteran_frame_unlocked": progress.veteran_frame_unlocked,
        "last_seed": progress.last_seed,
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)
