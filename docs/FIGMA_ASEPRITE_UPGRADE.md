# EchoZero Figma + Aseprite Upgrade

## Figma

- 文件：[EchoZero — Tactical Roguelike UI System](https://www.figma.com/design/E4aV4HLeGam7sZIQJgLSym)
- 页面 1：品牌封面、设计原则、代码色板、字体、间距和几何规则；
- 页面 2：Action Combat 与 Tactical Mode 的 1280×800 可编辑状态稿；
- 页面 3：Reward / Build 持久反馈与 Sprite Motion Specs。

2026-09-02 再次调用 Figma `get_metadata` 准备回读 Motion 时间线时，Starter 计划仍返回 `You've reached the Figma MCP tool call limit on the Starter plan`。账户核验为 Starter / View seat。该项属于外部账户额度阻断，未伪造节点 ID、关键帧或已完成状态；原始审计记录与额度恢复后的复核步骤见 `FIGMA_MOTION_AUDIT.md`。

Figma Starter 最多 3 页，因此多个状态使用独立画板分组，没有删减设计内容。通用 Material / Simple Design System 与项目的像素战术风冲突，未套用 SaaS 组件。

## Aseprite 兼容资产

本机未检测到 Aseprite。项目保留现有 Meowa 原图，并通过 `tools/build_aseprite_assets.py` 生成 Aseprite 可继续编辑的 PNG 图集与 JSON 标签。Renderer 优先加载图集，文件缺失时自动退回静态 Meowa 素材。

短帧只表达姿态，不改变坐标、伤害、冷却、AI 或 Tactical 结算。玩家动作由已有 LogicEvent 映射到 Idle / Move / Attack / Dodge / Hurt；敌人通过同一个 PreparedAction 倒计时进入 Prepared 脉冲。死亡扫描线仍消费既有 `died` 事件。

## UI 落地差异

- Tactical HUD 新增玩家化“因果链”说明，识别锁断、盾势和首尾回声等已有三拍关系；
- 动画资源统一为 64px 帧格、脚底锚点和最近邻缩放；
- Reduce Motion 固定到主帧，保留状态颜色与轮廓，不播放明显位移；
- 正式 HUD 继续使用中文玩家说明，英文只作为低权重系统标签。
