# ARCHITECTURE——技术架构

> 状态：第 00 阶段建议稿；核心方案确认后进入实现。

## 1. 架构目标

支持两关高质量 Demo、确定性因果预演和快速配置内容。非目标：通用引擎、ECS 框架、联网、数据库、地图编辑器、脚本语言。

## 2. 依赖方向

```text
pygame 输入 ─→ Scene/Controller ─→ domain Command
                                    ↓
JSON ─→ Config Loader ─→ Registry ─→ Simulator ─→ CombatState
                                    ↓             ↓
                              LogicEvent[] ─→ Renderer/Animation/Audio

Preview: clone(CombatState) ─→ 同一个 Simulator ─→ PreviewResult
```

`domain` 不知道窗口、图片、音频和动画；`presentation` 不决定伤害或 AI；`infrastructure` 只负责配置、路径和存档。MVP 使用确定性的“玩家三命令后敌人执行”流程，不实现敌我真正同步冲突。

## 3. 推荐目录

```text
main.py
src/
  app.py
  scenes/menu.py battle.py reward.py result.py
  domain/state.py commands.py effects.py simulation.py grid.py ai.py rng.py
  presentation/renderer.py animation.py hud.py audio.py
  infrastructure/config.py save.py paths.py
data/skills/ enemies/ levels/ rewards/ statuses/
assets/images/ audio/ fonts/
tests/
```

## 4. 核心数据结构

### `CombatState`

包含 `step`、网格、实体字典、占位映射、状态列表、规则节点、玩家 Build、敌人锁定意图和 RNG 状态引用。它是完整战斗事实，可深拷贝或通过明确 `clone()` 复制用于预演。

### `EntityState`

稳定 ID、阵营、格坐标、生命、属性、状态、当前意图。表现资源路径不放入领域对象。

### `Command`

不可变值对象：执行者、命令类型、目标、槽位、参数。每回合固定 3 个槽，空槽解析为待机；敌人意图也转换为命令，在玩家三条命令之后按可见编号执行。

### `LogicEvent`

模拟器输出的可序列化事实，如 `Moved`、`Damaged`、`Pushed`、`StatusApplied`、`NodeChanged`、`Died`。表现层按事件播放动画。

### 效果图

每个技能配置为有序效果节点：`condition → target_selector → effect`。首版只允许有限节点类型：伤害、移动、推动、加状态、生成危险格、重复命令。使用注册表映射类型到实现，禁止配置执行任意代码。

## 5. 回合与模拟

1. AI 在回合开始时移动并生成公开、锁定的意图和执行编号；
2. 收集三个玩家槽位，空槽转换为待机；
3. 节点规则对玩家命令作有限变换；
4. 按槽位 1～3 依次执行玩家命令；
5. 每条命令后立即处理推动阻挡、危险格、伤害和死亡；
6. 存活敌人按公开编号依次执行锁定意图；
7. 处理持续状态、节点周期和胜负；
8. 返回新状态和事件列表。

MVP 不需要优先队列；使用稳定列表即可保证确定性。只有后续确认敌人也进入三拍时间轴时，才引入 `(tick, priority, sequence)` 队列。

## 6. 预演一致性

`preview(state, commands)` 复制状态和 RNG，调用与 `execute_turn` 相同的纯模拟函数。真实执行在命令确认后调用同一函数，并把返回事件交给动画队列。

硬约束：

- 动画不能参与逻辑；
- 预演期间不得消费全局随机；
- 未知信息使用显式 `uncertain` 标记，禁止伪精确；
- 调试模式可计算预演终态哈希与执行终态哈希并比较。

## 7. 网格和 AI

- 小地图优先二维列表 + `dict[GridPos, entity_id]`；
- 无权最短路使用 BFS；有不同地形代价时使用 A*；
- 若多个敌人共享目标，可缓存单目标距离场；
- AI 枚举可达格与技能目标，计算效用：预期伤害、节点控制、接近目标、危险惩罚、打断价值；
- 最高分行为公开为意图，分数明细仅在 Debug 面板展示；
- 不做机器学习或不可解释黑箱。

## 8. 数据配置

启动时依次加载状态、效果、技能、敌人、关卡和奖励，校验 ID、字段类型、引用和数值范围。加载完成后转换成不可变定义对象。开发期配置错误直接失败并打印文件和字段；发布版显示简洁错误页并写日志。

## 9. 场景状态机

`MENU → BATTLE_L1 → REWARD → BATTLE_L2 → RESULT`，失败可从任一战斗进入 `RESULT`。场景切换由 `App` 持有一个当前场景即可，不建立 SceneManager 层级。

## 10. 存档与随机

保存 JSON：版本、运行种子、当前关卡、生命、插件 ID、解锁标记。Demo 只需关卡间自动存档和局外一次解锁。每局使用 `random.Random(seed)`；不使用模块级 `random`。

## 11. 性能预算

目标 60 FPS，逻辑回合可在单帧计算；预演建议低于 16 ms，必要时仅在命令变化时重算。小地图和少量实体无需多线程。渲染使用预缩放 Surface、Sprite 分层和批量绘制；不在每帧读盘或创建字体。

## 12. 测试策略

- 单元：命令、效果、冲突、状态、节点、AI 评分、配置；
- 性质：预演终态 = 执行终态；固定 seed 结果稳定；
- 集成：两关最短通路、奖励转场、胜负与存档；
- 冒烟：无音频设备仍可启动；缺少非关键资源使用占位；
- 发布：干净 Windows 用户目录运行 onedir 包。

## 13. 技术债警戒线

禁止出现 `GameManager/CombatManager/SkillManager/AudioManager` 全局互调、一个巨型 `game.py`、UI 直接扣血、技能名分支链、隐式全局 RNG、两套预演/执行规则、配置静默忽略错误。
