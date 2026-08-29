"""Small presentation-only contextual tutorial flow."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TutorialStep:
    step_id: str
    title: str
    body: str
    target: str


TUTORIAL_STEPS = {
    "timeline": TutorialStep(
        "timeline",
        "01 / 三拍编排",
        "每回合编排 3 个行动；点击两个槽位可以交换顺序。",
        "slots",
    ),
    "input": TutorialStep(
        "input",
        "02 / 填写行动",
        "选中槽位，再点棋盘；WASD / Q / E 也可以输入。",
        "slots",
    ),
    "intent": TutorialStep(
        "intent",
        "03 / ENEMY INTENT",
        "红色斜线格会在三拍之后受到敌人攻击。",
        "intent",
    ),
    "preview": TutorialStep(
        "preview",
        "04 / PREVIEW",
        "青色数字残影是同一模拟器算出的实际执行结果。",
        "preview",
    ),
    "execute": TutorialStep(
        "execute",
        "05 / EXECUTE",
        "确认预演后按 ENTER；三拍结束后，存活敌人才攻击。",
        "execute",
    ),
    "level2_order": TutorialStep(
        "level2_order",
        "LEVEL 2 / 实际顺序",
        "先看右侧顺序：稳定 1→2→3，逆相 3→2→1。",
        "rule",
    ),
    "anchor": TutorialStep(
        "anchor",
        "PHASE ANCHOR / 相位锚",
        "回合结束时站在绿色锚点，下一回合执行顺序保持。",
        "anchor",
    ),
    "phase_switch": TutorialStep(
        "phase_switch",
        "PHASE SWITCH / 相位切换",
        "未占据锚点时，回合结束后稳定与逆相会互相切换。",
        "rule",
    ),
}

LEVEL_ONE_STEPS = ("timeline", "input", "intent", "preview", "execute")
LEVEL_TWO_STEPS = ("level2_order", "anchor")


class ContextualTutorial:
    """Queue each concept once; never blocks battle input."""

    def __init__(self) -> None:
        self.current_id: str | None = None
        self.pending: list[str] = []
        self.shown: list[str] = []
        self.skipped = False

    @property
    def current(self) -> TutorialStep | None:
        if self.current_id is None:
            return None
        return TUTORIAL_STEPS[self.current_id]

    def begin_level_one(self) -> None:
        self._queue(LEVEL_ONE_STEPS)

    def begin_level_two(self) -> None:
        self._queue(LEVEL_TWO_STEPS)

    def show_once(self, step_id: str) -> None:
        if step_id not in TUTORIAL_STEPS:
            raise ValueError(f"Unknown tutorial step: {step_id}")
        self._queue((step_id,))

    def advance(self) -> None:
        if self.skipped:
            return
        self.current_id = None
        self._activate_next()

    def skip(self) -> None:
        self.skipped = True
        self.current_id = None
        self.pending.clear()

    def _queue(self, step_ids: tuple[str, ...]) -> None:
        if self.skipped:
            return
        for step_id in step_ids:
            if (
                step_id not in self.shown
                and step_id != self.current_id
                and step_id not in self.pending
            ):
                self.pending.append(step_id)
        self._activate_next()

    def _activate_next(self) -> None:
        if self.current_id is not None or not self.pending:
            return
        self.current_id = self.pending.pop(0)
        self.shown.append(self.current_id)
