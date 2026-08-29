"""Privacy-free local playtest summary for Stage07."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class EncounterMetric:
    attempt: int
    level: int
    encounter_id: str
    turns: int = 0
    hp: int = 0
    build: tuple[str, ...] = ()
    outcome: str = "in_progress"


class SessionMetrics:
    """Collect coarse gameplay facts without networking or personal data."""

    def __init__(self) -> None:
        self.run_seed: int | None = None
        self.retries = 0
        self.encounters: dict[str, EncounterMetric] = {}
        self.defeats: list[str] = []
        self.first_level_two_failure: str | None = None
        self.tutorial_shown: tuple[str, ...] = ()
        self.tutorial_skipped = False
        self.current_level = 0
        self.current_encounter = "menu"
        self.current_turn = 0
        self.current_hp = 0
        self.current_build: tuple[str, ...] = ()

    @property
    def attempt(self) -> int:
        return self.retries + 1

    def start_run(self, run_seed: int) -> None:
        self.run_seed = run_seed

    def record_retry(self) -> None:
        self.retries += 1

    def record_turn(
        self,
        level: int,
        encounter_id: str,
        turns: int,
        hp: int,
        build: tuple[str, ...],
        outcome: str,
    ) -> None:
        key = f"A{self.attempt}:L{level}:{encounter_id}"
        metric = self.encounters.setdefault(
            key, EncounterMetric(self.attempt, level, encounter_id)
        )
        metric.turns = max(metric.turns, turns)
        metric.hp = hp
        metric.build = tuple(build)
        metric.outcome = outcome
        self.snapshot(level, encounter_id, turns, hp, build)
        if outcome == "defeat":
            location = f"Attempt {self.attempt} / Level {level} / {encounter_id} / Turn {turns}"
            if location not in self.defeats:
                self.defeats.append(location)
            if level == 2 and self.first_level_two_failure is None:
                self.first_level_two_failure = location

    def snapshot(
        self,
        level: int,
        encounter_id: str,
        turn: int,
        hp: int,
        build: tuple[str, ...],
    ) -> None:
        self.current_level = level
        self.current_encounter = encounter_id
        self.current_turn = turn
        self.current_hp = hp
        self.current_build = tuple(build)

    def sync_tutorial(self, shown: list[str], skipped: bool) -> None:
        self.tutorial_shown = tuple(shown)
        self.tutorial_skipped = skipped

    def render(self) -> str:
        build = ", ".join(self.current_build) or "none"
        tutorial = ", ".join(self.tutorial_shown) or "none"
        lines = [
            "EchoZero Stage07 Session Summary",
            "Local only; no personal data or network transmission.",
            "",
            f"Run Seed: {self.run_seed if self.run_seed is not None else 'not started'}",
            f"Retry Count: {self.retries}",
            f"Current: Level {self.current_level} / {self.current_encounter} / Turn {self.current_turn}",
            f"Player HP: {self.current_hp}",
            f"Build: {build}",
            f"Tutorial Shown: {tutorial}",
            f"Tutorial Skipped: {'yes' if self.tutorial_skipped else 'no'}",
            "",
            "Encounters:",
        ]
        if self.encounters:
            for key in sorted(self.encounters):
                item = self.encounters[key]
                item_build = ", ".join(item.build) or "none"
                lines.append(
                    f"- {key}: turns={item.turns}, hp={item.hp}, "
                    f"outcome={item.outcome}, build={item_build}"
                )
        else:
            lines.append("- none")
        lines.extend(("", "Defeats:"))
        lines.extend(f"- {item}" for item in self.defeats)
        if not self.defeats:
            lines.append("- none")
        lines.extend(
            (
                "",
                "First Level 2 Failure:",
                self.first_level_two_failure or "none",
                "",
            )
        )
        return "\n".join(lines)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(), encoding="utf-8")
