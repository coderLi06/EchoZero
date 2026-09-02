from src.domain import CommandType, EncounterOutcome
from src.stage02_app import Stage02App


def test_stage02_app_executes_previewed_opening_and_restarts() -> None:
    app = Stage02App()
    assert not hasattr(app, "screen")
    assert not hasattr(app, "run")
    app._choose_slot(2)
    app._choose_slot(0)
    app._choose_slot(0)
    app._choose_slot(2)
    app._choose_slot(1)
    assert [command.command_type for command in app.encounter.commands] == [
        CommandType.PULL,
        CommandType.PUSH,
        CommandType.MOVE,
    ]
    app._execute()
    assert app.ui.verification_ok is True
    assert "charger" not in app.encounter.state.entities
    app._restart()
    assert app.encounter.outcome is EncounterOutcome.ONGOING
    assert "charger" in app.encounter.state.entities
