from __future__ import annotations

import random
from pathlib import Path

import pygame

from src.action_app import ActionApp
from src.domain import (
    ActionRunPhase,
    Command,
    CommandType,
    Direction,
    EnemyIntent,
    EntityState,
    Faction,
    GridPos,
    LogicEvent,
    state_fingerprint,
)
from src.infrastructure import MetaProgress, load_meta_progress, save_meta_progress
from src.presentation.action_renderer import (
    ACTION_TUTORIAL_BACK_RECT,
    ACTION_TUTORIAL_REPLAY_RECT,
    ACTION_TUTORIAL_SKIP_ALL_RECT,
    ACTION_TUTORIAL_SKIP_STEP_RECT,
    NEW_RUN_RECT,
    REWARD_RECTS,
    TACTICAL_CANCEL_RECT,
    TACTICAL_EXECUTE_RECT,
    TACTICAL_SLOT_RECTS,
    ActionRenderer,
    CELL_SIZE,
    COLORS,
    REWARD_KIND_LABELS,
)
from src.presentation.action_art import draw_hazard_tile, draw_player_actor, draw_unit_icon
from src.presentation.action_tutorial import ACTION_TUTORIAL_STEPS, ActionTutorial


def test_meta_progress_round_trip_and_unlock(tmp_path: Path) -> None:
    path = tmp_path / "meta.json"
    progress = MetaProgress()
    assert progress.record_result(False)
    assert progress.starting_core_bonus == 1
    save_meta_progress(path, progress)
    assert load_meta_progress(path) == progress


def test_bad_meta_file_falls_back_safely(tmp_path: Path) -> None:
    path = tmp_path / "meta.json"
    path.write_text("{bad", encoding="utf-8")
    assert load_meta_progress(path) == MetaProgress()


def test_new_run_uses_injected_seed_source_and_displays_seed(tmp_path: Path) -> None:
    source = random.Random(11)
    expected = random.Random(11).getrandbits(63)
    app = ActionApp(seed_source=source, meta_path=tmp_path / "meta.json")
    app.start_new_run()
    assert app.run_state is not None
    assert app.run_state.seed == expected
    assert load_meta_progress(tmp_path / "meta.json").last_seed == expected


def test_first_menu_start_runs_tutorial_before_consuming_seed(tmp_path: Path) -> None:
    source = random.Random(31)
    expected = random.Random(31).getrandbits(63)
    app = ActionApp(seed_source=source, meta_path=tmp_path / "meta.json")

    app._handle_key(pygame.K_RETURN, 0)

    assert app.tutorial.active
    assert app.run_state is None
    assert app.meta.last_seed is None

    app._handle_key(pygame.K_F1, 0)

    assert not app.tutorial.active
    assert app.tutorial.completed_once
    assert app.run_state is not None
    assert app.run_state.seed == expected


def test_wasd_keydown_moves_immediately_without_waiting_for_key_poll(tmp_path: Path) -> None:
    app = ActionApp(seed=41, meta_path=tmp_path / "meta.json")
    app.start_new_run()
    run = app.run_state
    assert run is not None and run.player is not None
    key_by_direction = {
        Direction.UP: pygame.K_w,
        Direction.RIGHT: pygame.K_d,
        Direction.DOWN: pygame.K_s,
        Direction.LEFT: pygame.K_a,
    }
    direction = next(
        candidate
        for candidate in Direction
        if run.player.pos.moved(candidate) in run.map.floor
        and run.state.entity_at(run.player.pos.moved(candidate)) is None
    )
    origin = run.player.pos

    app._handle_key(key_by_direction[direction], 0)

    assert run.player.pos == origin.moved(direction)
    assert app.player_pose == "move"


def test_logic_events_select_attack_dodge_skill_and_hurt_poses(tmp_path: Path) -> None:
    app = ActionApp(seed=42, meta_path=tmp_path / "meta.json")
    cases = (
        (LogicEvent("attack_missed", 0, "player"), "attack"),
        (LogicEvent("dodged", 0, "player", from_pos=GridPos(1, 1), to_pos=GridPos(2, 1)), "dodge"),
        (LogicEvent("pull_missed", 0, "player"), "skill"),
        (LogicEvent("damaged", 0, "enemy", "player", to_pos=GridPos(1, 1), amount=1), "hurt"),
    )
    for event, expected in cases:
        app._consume((event,))
        assert app.player_pose == expected


def test_action_tutorial_supports_back_and_step_skip() -> None:
    tutorial = ActionTutorial()
    tutorial.start()
    assert tutorial.progress == (1, len(ACTION_TUTORIAL_STEPS))
    assert not tutorial.skip_current()
    assert tutorial.progress[0] == 2
    tutorial.back()
    assert tutorial.progress[0] == 1
    tutorial.cancel()
    assert not tutorial.active
    assert not tutorial.completed_once


def test_tutorial_blocks_combat_input_and_replay_preserves_run(tmp_path: Path) -> None:
    app = ActionApp(seed=71, meta_path=tmp_path / "meta.json")
    app.start_new_run()
    run = app.run_state
    assert run is not None
    before_fingerprint = state_fingerprint(run.state)
    before_elapsed = run.elapsed
    before_timers = dict(run.enemy_timers)

    app._restart_action_tutorial()
    app._handle_key(pygame.K_w, 0)
    app._handle_key(pygame.K_q, 0)
    app._handle_key(pygame.K_e, 0)

    assert app.run_state is run
    assert state_fingerprint(run.state) == before_fingerprint
    assert run.elapsed == before_elapsed
    assert run.enemy_timers == before_timers

    app._handle_key(pygame.K_F1, 0)

    assert app.run_state is run
    assert state_fingerprint(run.state) == before_fingerprint


def test_cancel_initial_tutorial_returns_to_menu_without_seed(tmp_path: Path) -> None:
    app = ActionApp(seed=99, meta_path=tmp_path / "meta.json")
    app._request_new_run()
    app._handle_key(pygame.K_ESCAPE, 0)
    assert not app.tutorial.active
    assert app.run_state is None
    assert app.meta.last_seed is None


def test_tactical_reordering_changes_action_run_result(tmp_path: Path) -> None:
    app = ActionApp(seed=7, meta_path=tmp_path / "meta.json")
    app.start_new_run()
    run = app.run_state
    assert run is not None
    run.state.width = 5
    run.state.height = 5
    run.state.walls = {GridPos(4, 2)}
    run.state.entities = {
        "player": EntityState("player", Faction.PLAYER, GridPos(2, 2), 5, 5, "ECHO"),
        "enemy": EntityState("enemy", Faction.ENEMY, GridPos(3, 2), 2, 2, "追猎体", "melee"),
    }
    run.prepared_actions = {}
    run.state.enemy_intents = (
        EnemyIntent("enemy", GridPos(2, 2), 1, 1, "attack", "STRIKE"),
    )
    push_then_move = (
        Command("player", CommandType.PUSH, 1, Direction.RIGHT),
        Command("player", CommandType.MOVE, 2, Direction.UP),
        Command("player", CommandType.WAIT, 3),
    )
    move_then_push = (
        Command("player", CommandType.MOVE, 1, Direction.UP),
        Command("player", CommandType.PUSH, 2, Direction.RIGHT),
        Command("player", CommandType.WAIT, 3),
    )
    from src.domain import preview_turn

    first = preview_turn(run.state, push_then_move)
    second = preview_turn(run.state, move_then_push)
    assert "enemy" not in first.state.entities
    assert "enemy" in second.state.entities


def test_reward_sequences_change_across_seeds(tmp_path: Path) -> None:
    sequences = set()
    for seed in range(1, 6):
        app = ActionApp(seed=seed, meta_path=tmp_path / f"{seed}.json")
        app.start_new_run()
        run = app.run_state
        assert run is not None
        for enemy in run.active_enemies:
            run.state.entities.pop(enemy.entity_id)
        run.update(0.01)
        sequences.add(tuple(choice.reward_id for choice in run.reward_choices))
    assert len(sequences) >= 3


def test_action_renderer_all_core_scenes_draw_without_clipping(tmp_path: Path) -> None:
    pygame.init()
    try:
        surface = pygame.Surface((1280, 800))
        renderer = ActionRenderer(surface)
        app = ActionApp(seed=10303, meta_path=tmp_path / "meta.json")
        app.renderer = renderer
        renderer.draw(app)
        app._request_new_run()
        for _ in ACTION_TUTORIAL_STEPS:
            renderer.draw(app)
            if app.tutorial.advance():
                break
        app._finish_action_tutorial()
        app.start_new_run()
        renderer.draw(app)
        assert app.run_state is not None
        assert app.run_state.enter_tactical()
        renderer.draw(app)
        app.run_state.cancel_tactical()
        for enemy in app.run_state.active_enemies:
            app.run_state.state.entities.pop(enemy.entity_id)
        app.run_state.update(0.01)
        renderer.draw(app)
    finally:
        pygame.quit()


def test_action_ui_targets_are_large_and_tactical_has_escape() -> None:
    targets = (
        NEW_RUN_RECT,
        *REWARD_RECTS,
        *TACTICAL_SLOT_RECTS,
        TACTICAL_EXECUTE_RECT,
        TACTICAL_CANCEL_RECT,
        ACTION_TUTORIAL_REPLAY_RECT,
        ACTION_TUTORIAL_BACK_RECT,
        ACTION_TUTORIAL_SKIP_STEP_RECT,
        ACTION_TUTORIAL_SKIP_ALL_RECT,
    )
    assert all(rect.width >= 48 and rect.height >= 48 for rect in targets)


def test_action_visuals_use_large_cells_high_contrast_and_distinct_silhouettes() -> None:
    assert CELL_SIZE >= 56

    def luminance(color: tuple[int, int, int]) -> float:
        channels = []
        for value in color:
            component = value / 255
            channels.append(component / 12.92 if component <= 0.04045 else ((component + 0.055) / 1.055) ** 2.4)
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    contrast = (luminance(COLORS["text"]) + 0.05) / (luminance(COLORS["surface"]) + 0.05)
    assert contrast >= 4.5

    silhouettes = set()
    for kind in ("player", "melee", "charger", "ranged", "warden"):
        surface = pygame.Surface((72, 72), pygame.SRCALPHA)
        draw_unit_icon(surface, (36, 36), 22, kind, COLORS["cyan"], COLORS["text"])
        silhouettes.add(pygame.image.tobytes(surface, "RGBA"))
    assert len(silhouettes) == 5

    pose_frames = set()
    for pose in ("idle", "move", "attack", "dodge", "skill", "hurt"):
        surface = pygame.Surface((96, 96), pygame.SRCALPHA)
        draw_player_actor(surface, (48, 48), 20, pose, (1, 0), 0.55, COLORS["cyan"], COLORS["text"])
        pose_frames.add(pygame.image.tobytes(surface, "RGBA"))
    assert len(pose_frames) == 6

    first_fire = pygame.Surface((64, 64), pygame.SRCALPHA)
    second_fire = pygame.Surface((64, 64), pygame.SRCALPHA)
    tile = pygame.Rect(4, 4, 56, 56)
    draw_hazard_tile(first_fire, tile, COLORS["danger"], COLORS["warning"], 0.0)
    draw_hazard_tile(second_fire, tile, COLORS["danger"], COLORS["warning"], 0.24)
    assert pygame.image.tobytes(first_fire, "RGBA") != pygame.image.tobytes(second_fire, "RGBA")
    assert set(REWARD_KIND_LABELS.values()) == {"协议", "技能", "属性"}


def test_result_records_meta_once(tmp_path: Path) -> None:
    app = ActionApp(seed=9, meta_path=tmp_path / "meta.json")
    app.start_new_run()
    run = app.run_state
    assert run is not None
    run.phase = ActionRunPhase.DEFEAT
    app._record_result_if_needed()
    app._record_result_if_needed()
    assert app.meta.failed_runs == 1
    assert load_meta_progress(tmp_path / "meta.json").failed_runs == 1
