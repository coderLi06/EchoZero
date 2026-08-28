from pathlib import Path

import pygame

from src.domain import CommandType, LevelPhase
from src.presentation.stage03_renderer import CELL_SIZE, GRID_ORIGIN
from src.stage03_app import AppScene, Stage03App


def test_stage03_app_starts_from_formal_menu_with_debug_hidden() -> None:
    app = Stage03App()
    assert app.scene is AppScene.MENU
    assert app.ui.debug is False
    app._start_level()
    assert app.scene is AppScene.BATTLE
    assert [command.command_type for command in app.level_run.encounter.commands] == [
        CommandType.PUSH,
        CommandType.MOVE,
        CommandType.PULL,
    ]


def test_stage03_app_smoke_traverses_full_flow_and_clean_restart() -> None:
    app = Stage03App()
    app._run_flow_smoke()
    assert app.scene is AppScene.BATTLE
    assert app.level_run.phase is LevelPhase.BATTLE
    assert app.level_run.progress == (1, 3)
    assert app.level_run.completed_encounters == set()
    assert app.level_run.player_plugins == []


def test_two_click_swap_and_explicit_pull_are_reachable_from_keyboard() -> None:
    app = Stage03App()
    app._start_level()
    app._choose_slot(2)
    app._choose_slot(0)
    assert app.ui.selected_slot is None
    assert app.level_run.encounter.commands[0].command_type is CommandType.PULL

    app._choose_slot(0)
    app._handle_key(pygame.K_e)
    assert app.ui.selected_slot is None
    assert app.level_run.encounter.commands[0].command_type is CommandType.PULL
    assert app.level_run.encounter.commands[0].target_entity_id == "charger_alpha"


def test_formal_keyboard_and_mouse_controls_can_clear_level_one() -> None:
    app = Stage03App()
    app._handle_key(pygame.K_RETURN)

    # P-M-L -> L-P-M, using two visible two-click swaps.
    for index in (2, 0, 1, 2):
        app._choose_slot(index)
    app._handle_key(pygame.K_RETURN)
    assert app.scene is AppScene.REWARD

    app._handle_key(pygame.K_1)
    app._handle_key(pygame.K_RETURN)
    assert app.level_run.progress == (3, 3)

    for index in (2, 0, 1, 2):
        app._choose_slot(index)
    app._handle_key(pygame.K_RETURN)

    for key in (pygame.K_1, pygame.K_d, pygame.K_2, pygame.K_d, pygame.K_RETURN):
        app._handle_key(key)
    for key in (
        pygame.K_1,
        pygame.K_w,
        pygame.K_2,
        pygame.K_d,
        pygame.K_3,
        pygame.K_d,
        pygame.K_RETURN,
    ):
        app._handle_key(key)

    sniper_cell = (
        GRID_ORIGIN[0] + 6 * CELL_SIZE + CELL_SIZE // 2,
        GRID_ORIGIN[1] + 3 * CELL_SIZE + CELL_SIZE // 2,
    )
    app._handle_key(pygame.K_1)
    app._handle_click(sniper_cell, 1)
    app._handle_key(pygame.K_2)
    app._handle_key(pygame.K_e)
    app._handle_key(pygame.K_3)
    app._handle_click(sniper_cell, 1)
    app._handle_key(pygame.K_RETURN)

    assert app.scene is AppScene.RESULT
    assert app.level_run.phase is LevelPhase.LEVEL_CLEAR
    assert app.level_run.completed_encounters == {
        "sequence_calibration",
        "protocol_trial",
        "dual_lock_climax",
    }


def test_stage03_app_reports_missing_content_without_crashing(tmp_path: Path) -> None:
    app = Stage03App(data_root=tmp_path)
    assert app.scene is AppScene.ERROR
    assert app.load_error is not None
    assert "Missing content file" in app.load_error
