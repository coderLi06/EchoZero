"""Stage 01 固定强对比演示局面。"""

from src.domain import Command, CommandType, CombatState, Direction, EnemyIntent, EntityState, Faction, GridPos


def create_demo_state() -> CombatState:
    return CombatState(
        width=8,
        height=6,
        entities={
            "player": EntityState("player", Faction.PLAYER, GridPos(1, 2), 3, 3, "执行者"),
            "sniper": EntityState("sniper", Faction.ENEMY, GridPos(3, 2), 1, 1, "校验射手"),
        },
        walls={GridPos(5, 1), GridPos(5, 2), GridPos(5, 3)},
        enemy_intents=(EnemyIntent("sniper", GridPos(1, 3), damage=2, order=1),),
    )


def default_commands() -> list[Command]:
    """故意失败的顺序：推击落空、踏入锁定格、斜线牵引失败。"""
    return [
        Command("player", CommandType.PUSH, 1, direction=Direction.RIGHT),
        Command("player", CommandType.MOVE, 2, direction=Direction.DOWN),
        Command("player", CommandType.PULL, 3, target_entity_id="sniper"),
    ]


def winning_commands() -> list[Command]:
    defaults = default_commands()
    return [defaults[2].in_slot(1), defaults[0].in_slot(2), defaults[1].in_slot(3)]

