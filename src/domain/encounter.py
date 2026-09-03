"""Stage02 测试 Encounter 的多回合流程、胜负和重开。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .ai import prepare_enemy_turn
from .model import (
    Command, CommandType, CombatState, Direction, Faction, LogicEvent,
    SimulationResult,
)
from .simulation import execute_turn, preview_turn


class EncounterOutcome(str, Enum):
    ONGOING = "ongoing"
    VICTORY = "victory"
    DEFEAT = "defeat"


@dataclass(frozen=True)
class TurnResolution:
    result: SimulationResult
    preparation_events: tuple[LogicEvent, ...]
    outcome: EncounterOutcome


class Encounter:
    def __init__(self, initial_state: CombatState) -> None:
        self._initial_state = initial_state.clone()
        self.restart()

    def restart(self) -> None:
        self.state, self.preparation_events = prepare_enemy_turn(self._initial_state)
        self.commands = [Command("player", CommandType.WAIT, slot) for slot in range(1, 4)]
        self.outcome = self._outcome(self.state)

    def set_command(self, command: Command) -> None:
        if self.outcome is not EncounterOutcome.ONGOING:
            raise RuntimeError("Encounter has already ended")
        if command.actor_id != "player" or not 1 <= command.slot <= 3:
            raise ValueError("Only player commands in slots 1..3 are accepted")
        if command.command_type in {CommandType.MOVE, CommandType.PUSH} and command.direction is None:
            raise ValueError(f"{command.command_type.value} requires a direction")
        if command.command_type is CommandType.PULL and command.target_entity_id not in self.state.entities:
            raise ValueError("Pull requires a living target")
        updated = list(self.commands)
        updated[command.slot - 1] = command
        self.commands = updated

    def swap_slots(self, first: int, second: int) -> None:
        if self.outcome is not EncounterOutcome.ONGOING:
            return
        if not (0 <= first < 3 and 0 <= second < 3):
            raise IndexError("Slot index must be 0..2")
        self.commands[first], self.commands[second] = self.commands[second], self.commands[first]
        self.commands = [command.in_slot(index + 1) for index, command in enumerate(self.commands)]

    def preview(self) -> SimulationResult:
        return preview_turn(self.state, self.commands)

    def confirm_turn(self) -> TurnResolution:
        if self.outcome is not EncounterOutcome.ONGOING:
            raise RuntimeError("Encounter has already ended")
        result = execute_turn(self.state, self.commands)
        outcome = self._outcome(result.state)
        preparation_events: tuple[LogicEvent, ...] = ()
        next_state = result.state
        if outcome is EncounterOutcome.ONGOING:
            next_state, preparation_events = prepare_enemy_turn(result.state)
            outcome = self._outcome(next_state)
        self.state = next_state
        self.preparation_events = preparation_events
        self.outcome = outcome
        self.commands = (
            self._commands_for_next_turn(next_state)
            if outcome is EncounterOutcome.ONGOING
            else [Command("player", CommandType.WAIT, slot) for slot in range(1, 4)]
        )
        return TurnResolution(result, preparation_events, outcome)

    def _commands_for_next_turn(self, state: CombatState) -> list[Command]:
        """Keep reusable commands and replace dead-target pulls with a safe suggestion."""
        commands: list[Command] = []
        for command in self.commands:
            target_is_dead = (
                command.command_type is CommandType.PULL
                and command.target_entity_id not in state.entities
            )
            commands.append(
                self._approach_surviving_enemy(state, command.slot)
                if target_is_dead
                else command.in_slot(command.slot)
            )
        return commands

    @staticmethod
    def _approach_surviving_enemy(state: CombatState, slot: int) -> Command:
        player = state.entities.get("player")
        enemies = sorted(
            (entity for entity in state.entities.values() if entity.faction is Faction.ENEMY),
            key=lambda entity: (
                player.pos.manhattan_distance(entity.pos) if player is not None else 0,
                entity.entity_id,
            ),
        )
        if player is None or not enemies:
            return Command("player", CommandType.WAIT, slot)
        target = enemies[0]
        for direction in Direction:
            if player.pos.moved(direction) == target.pos:
                return Command("player", CommandType.PUSH, slot, direction)
        occupied = {
            entity.pos for entity in state.entities.values()
            if entity.entity_id != player.entity_id
        }
        legal_directions = [
            direction for direction in Direction
            if state.in_bounds(player.pos.moved(direction))
            and player.pos.moved(direction) not in state.walls
            and player.pos.moved(direction) not in occupied
        ]
        if not legal_directions:
            return Command("player", CommandType.WAIT, slot)
        direction = min(
            legal_directions,
            key=lambda item: player.pos.moved(item).manhattan_distance(target.pos),
        )
        return Command("player", CommandType.MOVE, slot, direction)

    @staticmethod
    def _outcome(state: CombatState) -> EncounterOutcome:
        has_player = any(entity.faction is Faction.PLAYER for entity in state.entities.values())
        has_enemy = any(entity.faction is Faction.ENEMY for entity in state.entities.values())
        if not has_player:
            return EncounterOutcome.DEFEAT
        if not has_enemy:
            return EncounterOutcome.VICTORY
        return EncounterOutcome.ONGOING
