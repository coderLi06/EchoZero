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
    TimelineRule,
)
from .simulation import execute_turn, preview_turn, simulate_turn, state_fingerprint
from .ai import prepare_enemy_turn
from .encounter import Encounter, EncounterOutcome, TurnResolution
from .content import EncounterDefinition, EnemySpawn, LevelDefinition, PluginDefinition
from .level import LevelPhase, LevelRun
from .reward import RewardPool

__all__ = [
    "Command", "CommandType", "CombatState", "Direction", "EnemyIntent",
    "EntityState", "Faction", "GridPos", "LogicEvent", "SimulationResult", "TimelineRule",
    "execute_turn", "preview_turn", "simulate_turn", "state_fingerprint",
    "prepare_enemy_turn", "Encounter", "EncounterOutcome", "TurnResolution",
    "EncounterDefinition", "EnemySpawn", "LevelDefinition", "PluginDefinition",
    "LevelPhase", "LevelRun", "RewardPool",
]
