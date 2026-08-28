from src.app import GrayboxApp
from src.domain import CommandType


def test_two_click_swaps_can_reach_winning_order_and_execute() -> None:
    app = GrayboxApp()
    app._choose_slot(2)
    app._choose_slot(0)
    app._choose_slot(0)
    app._choose_slot(2)
    app._choose_slot(1)

    assert [command.command_type for command in app.commands] == [
        CommandType.PULL,
        CommandType.PUSH,
        CommandType.MOVE,
    ]

    app._execute()

    assert app.ui.executed is True
    assert app.ui.verification_ok is True
    assert "sniper" not in app.state.entities


def test_reset_restores_initial_losing_preview() -> None:
    app = GrayboxApp()
    app.commands.reverse()
    app._reset()

    assert [command.command_type for command in app.commands] == [
        CommandType.PUSH,
        CommandType.MOVE,
        CommandType.PULL,
    ]
    assert app.preview.state.entities["player"].hp == 1
