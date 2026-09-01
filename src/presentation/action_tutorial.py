"""Presentation-only Action Run tutorial shown before real-time simulation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActionTutorialStep:
    step_id: str
    title: str
    body: str
    target: str


ACTION_TUTORIAL_STEPS = (
    ActionTutorialStep(
        "simulation",
        "动作模拟教学",
        "这里不会生成正式 Seed，也不会启动敌人计时。先认识操作和因果系统，再进入真正的 Run。",
        "board",
    ),
    ActionTutorialStep(
        "core",
        "CORE 与 SHIELD",
        "CORE 是生命；降到 0 本局结束。SHIELD 会优先吸收伤害，部分协议会改变它。",
        "core",
    ),
    ActionTutorialStep(
        "movement",
        "WASD 实时移动",
        "常态战斗不会等待回合。按下 WASD 会立即移动；看到持续火焰的危险格时应绕开。",
        "movement",
    ),
    ActionTutorialStep(
        "attack",
        "攻击、闪避与牵引",
        "左键或 Space 攻击并击退；Shift+WASD 闪避；E 沿面对方向牵引敌人。冷却条就绪后可再次使用。",
        "action_controls",
    ),
    ActionTutorialStep(
        "intent",
        "BEHAVIOR TREE / ENEMY INTENT",
        "敌人名称后的 Action 是行为树当前准备执行的动作；红线和目标圈把同一个 Action 画在地图上。",
        "intent",
    ),
    ActionTutorialStep(
        "tactical",
        "Q / TACTICAL MODE",
        "危险时按 Q 冻结战斗。敌人停止计时，你可以安全读取 Intent，并在执行后进入冷却。",
        "tactical",
    ),
    ActionTutorialStep(
        "timeline",
        "三拍编排与 PREVIEW",
        "选择 1/2/3 拍写入 Move、Push、Pull、Shield 或 Wait。Preview 来自真实模拟器副本，换序会改变结果。",
        "timeline",
    ),
    ActionTutorialStep(
        "rewards",
        "随机奖励与完整 Run",
        "清场后从协议、技能或属性中三选一；构筑会进入下一张程序地图，第三场是 Boss。",
        "rewards",
    ),
    ActionTutorialStep(
        "ready",
        "准备开始正式 Run",
        "接下来才会生成并保存 Seed。正式战斗不会再自动弹出教学；需要复习时点击右下角“重新进入教学”。",
        "ready",
    ),
)


class ActionTutorial:
    """Blocking, reversible guide that never owns or changes game state."""

    def __init__(self) -> None:
        self.index = 0
        self.active = False
        self.completed_once = False
        self.skipped = False

    @property
    def current(self) -> ActionTutorialStep | None:
        if not self.active:
            return None
        return ACTION_TUTORIAL_STEPS[self.index]

    @property
    def progress(self) -> tuple[int, int]:
        return (self.index + 1, len(ACTION_TUTORIAL_STEPS))

    def start(self) -> None:
        self.index = 0
        self.active = True
        self.skipped = False

    def advance(self) -> bool:
        if not self.active:
            return False
        if self.index + 1 < len(ACTION_TUTORIAL_STEPS):
            self.index += 1
            return False
        self.active = False
        self.completed_once = True
        return True

    def back(self) -> None:
        if self.active:
            self.index = max(0, self.index - 1)

    def skip_current(self) -> bool:
        return self.advance()

    def skip_all(self) -> bool:
        if not self.active:
            return False
        self.active = False
        self.completed_once = True
        self.skipped = True
        return True

    def cancel(self) -> None:
        self.active = False
