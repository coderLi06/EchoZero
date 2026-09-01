"""Presentation-only guided simulation shown before the formal battle."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TutorialStep:
    step_id: str
    title: str
    body: str
    target: str


TUTORIAL_STEPS = {
    "simulation": TutorialStep(
        "simulation",
        "模拟教学",
        "这里的讲解不会执行命令或消耗回合；先认识画面，再进入正式对局。",
        "board",
    ),
    "core": TutorialStep(
        "core",
        "CORE 与 SHIELD",
        "CORE 是生命值，降到 0 即失败；SHIELD 会优先吸收本回合伤害。",
        "core",
    ),
    "intent": TutorialStep(
        "intent",
        "ENEMY INTENT / 敌人意图",
        "红色斜线和编号表示敌人锁定的位置；玩家三拍结束后才会结算攻击。",
        "intent",
    ),
    "timeline": TutorialStep(
        "timeline",
        "三拍命令链",
        "每回合安排 3 个行动；槽位数字就是执行拍次，交换槽位会改变因果结果。",
        "slots",
    ),
    "actions": TutorialStep(
        "actions",
        "MOVE / PUSH / PULL / SHIELD / WAIT",
        "移动、推击、牵引、护盾与待机组成命令；点击槽位后再选择棋盘目标。",
        "slots",
    ),
    "preview": TutorialStep(
        "preview",
        "PREVIEW / 因果预演",
        "青色数字残影和终态来自真实结算器的副本；换序后这里会立即重新计算。",
        "preview",
    ),
    "protocol": TutorialStep(
        "protocol",
        "PROTOCOL / 协议构筑",
        "协议会改写命令规则或提供联动效果；获得后会常驻显示在这里。",
        "protocol",
    ),
    "execute": TutorialStep(
        "execute",
        "EXECUTE / 执行",
        "确认预演后执行三拍；正式对局中可点击按钮，也可以按 Enter 或空格。",
        "execute",
    ),
    "ready": TutorialStep(
        "ready",
        "准备进入正式对局",
        "教学结束后不会再自动弹出提示；需要复习时，点击右下角“重新进入教学”。",
        "board",
    ),
}

CORE_TUTORIAL_STEPS = (
    "simulation",
    "core",
    "intent",
    "timeline",
    "actions",
    "preview",
    "protocol",
    "execute",
    "ready",
)


class ContextualTutorial:
    """Run a blocking guided simulation once, with an explicit replay path."""

    def __init__(self) -> None:
        self.current_id: str | None = None
        self.pending: list[str] = []
        self.shown: list[str] = []
        self.skipped = False
        self.started = False
        self.completed = False

    @property
    def current(self) -> TutorialStep | None:
        if self.current_id is None:
            return None
        return TUTORIAL_STEPS[self.current_id]

    def begin_initial(self) -> None:
        if not self.started:
            self.restart()

    def restart(self) -> None:
        self.started = True
        self.completed = False
        self.skipped = False
        self.current_id = None
        self.pending = list(CORE_TUTORIAL_STEPS)
        self._activate_next()

    @property
    def active(self) -> bool:
        return self.current_id is not None

    @property
    def progress(self) -> tuple[int, int]:
        if self.current_id is None:
            return (0, len(CORE_TUTORIAL_STEPS))
        return (
            CORE_TUTORIAL_STEPS.index(self.current_id) + 1,
            len(CORE_TUTORIAL_STEPS),
        )

    def advance(self) -> None:
        if self.skipped:
            return
        self.current_id = None
        self._activate_next()

    def skip_current(self) -> None:
        self.advance()

    def skip_all(self) -> None:
        self.skipped = True
        self.completed = True
        self.current_id = None
        self.pending.clear()

    def _activate_next(self) -> None:
        if self.current_id is not None:
            return
        if not self.pending:
            self.completed = True
            return
        self.current_id = self.pending.pop(0)
        if self.current_id not in self.shown:
            self.shown.append(self.current_id)
