"""Deterministic weighted reward candidates with build legality checks."""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence

from .content import PluginDefinition


class RewardPool:
    def __init__(
        self,
        definitions: Mapping[str, PluginDefinition],
        rng: random.Random,
    ) -> None:
        self._definitions = dict(definitions)
        self._rng = rng

    def candidates(
        self,
        pool_ids: Sequence[str],
        count: int,
        build: Mapping[str, int],
    ) -> tuple[PluginDefinition, ...]:
        eligible = [
            self._definitions[plugin_id]
            for plugin_id in pool_ids
            if self._is_eligible(self._definitions[plugin_id], build)
        ]
        if len(eligible) < count:
            raise ValueError(
                f"Reward pool has {len(eligible)} eligible entries, needs {count}"
            )
        selected: list[PluginDefinition] = []
        remaining = list(eligible)
        while len(selected) < count:
            total = sum(item.weight for item in remaining)
            roll = self._rng.randrange(total)
            cursor = 0
            for index, item in enumerate(remaining):
                cursor += item.weight
                if roll < cursor:
                    selected.append(remaining.pop(index))
                    break
        selected_ids = {item.plugin_id for item in selected}
        return tuple(
            self._definitions[plugin_id]
            for plugin_id in pool_ids
            if plugin_id in selected_ids
        )

    def _is_eligible(
        self, definition: PluginDefinition, build: Mapping[str, int]
    ) -> bool:
        if build.get(definition.plugin_id, 0) >= definition.max_stack:
            return False
        owned = {plugin_id for plugin_id, stacks in build.items() if stacks > 0}
        if not set(definition.requirements).issubset(owned):
            return False
        if set(definition.conflicts) & owned:
            return False
        return not any(
            definition.plugin_id in self._definitions[plugin_id].conflicts
            for plugin_id in owned
        )
