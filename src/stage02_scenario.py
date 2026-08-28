"""Stage02 专用测试 Encounter；不是正式第一关内容。"""

from src.domain import Command, CommandType, CombatState, Direction, EntityState, Faction, GridPos


def create_stage02_state() -> CombatState:
    return CombatState(
        width=8,
        height=6,
        entities={
            "player": EntityState("player", Faction.PLAYER, GridPos(1, 3), 5, 5, "执行者"),
            "charger": EntityState("charger", Faction.ENEMY, GridPos(4, 3), 1, 1, "突进体", "charger"),
            "sniper": EntityState("sniper", Faction.ENEMY, GridPos(6, 1), 2, 2, "校验射手", "sniper"),
        },
        walls={GridPos(7, 1), GridPos(4, 1), GridPos(4, 2), GridPos(4, 4)},
    )


def opening_commands() -> list[Command]:
    """同三条命令的故意失败顺序；交换为牵引→推击→移动可安全击杀突进体。"""
    return [
        Command("player", CommandType.PUSH, 1, direction=Direction.RIGHT),
        Command("player", CommandType.MOVE, 2, direction=Direction.DOWN),
        Command("player", CommandType.PULL, 3, target_entity_id="charger"),
    ]
