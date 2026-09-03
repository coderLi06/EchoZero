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
        "近战、远程与切换",
        "按 C 切换攻击模式：近战距离 1、全伤并击退；远程沿面对方向命中 3 格内首个敌人、伤害减半且不击退。Space/左键攻击，Shift+WASD 闪避，E 牵引。",
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
        "Q 会给出 7 条可用动作。用 1～7 选择、W/S 调整优先级；前三项组成实际三拍，Preview 会随排序即时变化。",
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
