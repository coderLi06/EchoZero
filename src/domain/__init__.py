"""不依赖 pygame 的战斗领域模型。"""

from .model import (
    Command,
    CommandType,
    CombatState,
    Direction,
    EnemyIntent,
    EntityState,
    Faction,
    GridPos,
    LogicEvent,
    SimulationResult,
)
from .simulation import execute_turn, preview_turn, simulate_turn, state_fingerprint
from .ai import prepare_enemy_turn
from .encounter import Encounter, EncounterOutcome, TurnResolution

__all__ = [
    "Command", "CommandType", "CombatState", "Direction", "EnemyIntent",
    "EntityState", "Faction", "GridPos", "LogicEvent", "SimulationResult",
    "execute_turn", "preview_turn", "simulate_turn", "state_fingerprint",
    "prepare_enemy_turn", "Encounter", "EncounterOutcome", "TurnResolution",
]
