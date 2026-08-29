"""Pure Level 1 progression: encounters, reward choice, inheritance and clear."""

from __future__ import annotations

import random
from enum import Enum

from .content import EncounterDefinition, LevelDefinition, PluginDefinition
from .encounter import Encounter, EncounterOutcome, TurnResolution
from .model import CombatState, EntityState, Faction
from .reward import RewardPool


class LevelPhase(str, Enum):
    BATTLE = "battle"
    REWARD = "reward"
    LEVEL_CLEAR = "level_clear"
    DEFEAT = "defeat"


class LevelRun:
    """Own one deterministic run without importing pygame or presentation code."""

    def __init__(
        self,
        definition: LevelDefinition,
        plugins: dict[str, PluginDefinition],
        seed: int | None = None,
        initial_player_hp: int | None = None,
        initial_plugins: tuple[str, ...] = (),
    ) -> None:
        if not definition.encounters:
            raise ValueError("Level requires at least one encounter")
        self.definition = definition
        self.plugin_definitions = dict(plugins)
        self._initial_player_hp = (
            definition.player_max_hp if initial_player_hp is None else initial_player_hp
        )
        if not 1 <= self._initial_player_hp <= definition.player_max_hp:
            raise ValueError("Initial player HP must be within the level maximum")
        self._initial_plugins = tuple(initial_plugins)
        self._validate_initial_build()
        self.restart(definition.seed if seed is None else seed)

    def restart(self, seed: int | None = None) -> None:
        if seed is not None:
            self.run_seed = seed
        elif not hasattr(self, "run_seed"):
            self.run_seed = self.definition.seed
        self._rng = random.Random(self.run_seed)
        self._reward_pool = RewardPool(self.plugin_definitions, self._rng)
        self.encounter_index = 0
        self.player_hp = self._initial_player_hp
        self.player_plugins = list(self._initial_plugins)
        self.player_build: dict[str, int] = {}
        for plugin_id in self.player_plugins:
            self.player_build[plugin_id] = self.player_build.get(plugin_id, 0) + 1
        self._reward_choices: tuple[PluginDefinition, ...] = ()
        self.completed_encounters: set[str] = set()
        self.phase = LevelPhase.BATTLE
        self.encounter = self._create_encounter(self.current_definition)

    @property
    def current_definition(self) -> EncounterDefinition:
        return self.definition.encounters[self.encounter_index]

    @property
    def progress(self) -> tuple[int, int]:
        return self.encounter_index + 1, len(self.definition.encounters)

    @property
    def reward_choices(self) -> tuple[PluginDefinition, ...]:
        if self.phase is not LevelPhase.REWARD:
            return ()
        return self._reward_choices

    @property
    def build_summary(self) -> tuple[tuple[PluginDefinition, int], ...]:
        return tuple(
            (definition, self.player_build[plugin_id])
            for plugin_id, definition in self.plugin_definitions.items()
            if self.player_build.get(plugin_id, 0) > 0
        )

    def confirm_turn(self) -> TurnResolution:
        if self.phase is not LevelPhase.BATTLE:
            raise RuntimeError(f"Cannot confirm a turn during {self.phase.value}")
        resolution = self.encounter.confirm_turn()
        if resolution.outcome is EncounterOutcome.DEFEAT:
            self.phase = LevelPhase.DEFEAT
        elif resolution.outcome is EncounterOutcome.VICTORY:
            self._settle_victory()
        return resolution

    def choose_reward(self, plugin_id: str) -> None:
        if self.phase is not LevelPhase.REWARD:
            raise RuntimeError("Reward choice is not active")
        offered = {item.plugin_id for item in self._reward_choices}
        if plugin_id not in offered:
            raise ValueError(f"Plugin {plugin_id!r} is not offered")
        definition = self.plugin_definitions[plugin_id]
        if self.player_build.get(plugin_id, 0) >= definition.max_stack:
            raise ValueError(f"Plugin {plugin_id!r} reached max stack")
        self.player_plugins.append(plugin_id)
        self.player_build[plugin_id] = self.player_build.get(plugin_id, 0) + 1
        self._reward_choices = ()
        self._start_next_encounter()

    def _settle_victory(self) -> None:
        encounter_id = self.current_definition.encounter_id
        if encounter_id in self.completed_encounters:
            raise RuntimeError(f"Encounter {encounter_id!r} was already settled")
        player = self.encounter.state.entities.get("player")
        if player is None:
            raise RuntimeError("Victory state has no player")
        self.player_hp = player.hp
        self.completed_encounters.add(encounter_id)
        if self.encounter_index == len(self.definition.encounters) - 1:
            self.phase = LevelPhase.LEVEL_CLEAR
        elif self.current_definition.reward_pool:
            self.phase = LevelPhase.REWARD
            self._reward_choices = self._reward_pool.candidates(
                self.current_definition.reward_pool,
                self.current_definition.reward_count,
                self.player_build,
            )
        else:
            self._start_next_encounter()

    def _start_next_encounter(self) -> None:
        if self.encounter_index >= len(self.definition.encounters) - 1:
            self.phase = LevelPhase.LEVEL_CLEAR
            return
        self.encounter_index += 1
        self.phase = LevelPhase.BATTLE
        self.encounter = self._create_encounter(self.current_definition)

    def _create_encounter(self, definition: EncounterDefinition) -> Encounter:
        entities = {
            "player": EntityState(
                "player",
                Faction.PLAYER,
                definition.player_spawn,
                self.player_hp,
                self.definition.player_max_hp,
                "执行者·零",
            )
        }
        for enemy in definition.enemies:
            entities[enemy.entity_id] = EntityState(
                enemy.entity_id,
                Faction.ENEMY,
                enemy.pos,
                enemy.hp,
                enemy.hp,
                enemy.display_name,
                enemy.enemy_kind,
            )
        return Encounter(
            CombatState(
                width=self.definition.width,
                height=self.definition.height,
                entities=entities,
                walls=set(definition.walls),
                player_plugins=tuple(self.player_plugins),
                player_plugin_effects=tuple(
                    self.plugin_definitions[plugin_id].effect_type
                    for plugin_id in self.player_plugins
                ),
                timeline_rules=definition.rule_cycle,
                rule_nodes=definition.rule_nodes,
            )
        )

    def _validate_initial_build(self) -> None:
        counts: dict[str, int] = {}
        for plugin_id in self._initial_plugins:
            if plugin_id not in self.plugin_definitions:
                raise ValueError(f"Unknown initial plugin {plugin_id!r}")
            counts[plugin_id] = counts.get(plugin_id, 0) + 1
            if counts[plugin_id] > self.plugin_definitions[plugin_id].max_stack:
                raise ValueError(f"Initial plugin {plugin_id!r} exceeds max stack")
