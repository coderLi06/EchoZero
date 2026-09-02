# EchoZero Figma Motion 元数据审计

> 审计日期：2026-09-02；Figma 文件：[EchoZero — Tactical Roguelike UI System](https://www.figma.com/design/E4aV4HLeGam7sZIQJgLSym)

## 本次结果

调用 Figma `get_metadata(fileKey=E4aV4HLeGam7sZIQJgLSym)` 时，服务返回：

```text
You've reached the Figma MCP tool call limit on the Starter plan.
```

随后通过账户核验确认当前席位为 `Starter / View`。因此无法安全取得第三页节点 ID，也不能在不知道目标节点的情况下调用 `get_motion_context` 或写入关键帧。项目没有猜测节点 ID，也没有把截图误报成 Motion 元数据。

## 已有可复核 Motion 证据

- Figma 第三页已包含 Reward / Build / Sprite Motion Specs 静态设计稿；
- `assets/aseprite/*.json` 保存 Idle / Move / Attack / Dodge / Hurt / Prepared / Hit / Death 的帧区间与时长；
- `src/action_app.py` 的 LogicEvent 姿态是运行时动画唯一输入；
- Reduce Motion 固定主帧，表现动画不参与伤害、位置或 AI 结算；
- `tests/test_action_assets.py` 验证图集帧格、标签和姿态选择。

## 额度恢复后的唯一收尾步骤

1. 对文件调用 `get_metadata`，取得第三页及 Motion Spec 顶层画板的真实节点 ID；
2. 对该画板调用递归 `get_motion_context`，记录 animated-node inventory、timeline、duration、keyframes 与 easing；
3. 若现有节点没有 Motion track，再使用 `use_figma` 按 0.25～0.7 秒、`EASE_OUT` / `EASE_IN_AND_OUT` 的项目节奏补充，并返回全部 mutated node IDs；
4. 再次回读 `manualKeyframeTracks`、`animationStyles` 与 `timelines`，把真实节点 ID 和结果写回本文件。

在以上调用成功前，本项保持“外部阻断”，不标记完成。
