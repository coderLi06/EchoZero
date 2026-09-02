"""Lightweight Stage02 regression harness; the retired pygame UI no longer ships."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain import Encounter, EncounterOutcome, LogicEvent, state_fingerprint
from src.stage02_scenario import create_stage02_state, opening_commands


@dataclass
class UiState:
    selected_slot: int | None = None
    verification_ok: bool | None = None
    feedback: str = "Stage02 回归夹具：验证换序、同源预演与重开。"


class Stage02App:
    """Compatibility facade kept only for the historical Stage02 regression test."""

    def __init__(self, smoke_test: bool = False) -> None:
        self.smoke_test = smoke_test
        self.ui = UiState()
        self.events: tuple[LogicEvent, ...] = ()
        self._restart()

    @property
    def preview(self):
        return self.encounter.preview()

    def _restart(self) -> None:
        self.encounter = Encounter(create_stage02_state())
        for command in opening_commands():
            self.encounter.set_command(command)
        self.events = self.encounter.preparation_events
        self.ui = UiState()

    def _choose_slot(self, index: int) -> None:
        if self.encounter.outcome is not EncounterOutcome.ONGOING:
            return
        if self.ui.selected_slot is None:
            self.ui.selected_slot = index
        elif self.ui.selected_slot == index:
            self.ui.selected_slot = None
        else:
            self.encounter.swap_slots(self.ui.selected_slot, index)
            self.ui.selected_slot = index

    def _execute(self) -> None:
        if self.encounter.outcome is not EncounterOutcome.ONGOING:
            return
        expected = state_fingerprint(self.preview.state)
        resolution = self.encounter.confirm_turn()
        self.ui.verification_ok = state_fingerprint(resolution.result.state) == expected
        self.events = resolution.result.events + resolution.preparation_events
        self.ui.selected_slot = None
        self.ui.feedback = "回归回合完成：预演与执行终态已校验。"
