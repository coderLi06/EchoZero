# ARCHITECTURE——技术架构

> 状态：Stage04 随机奖励与 Build 构筑已落地；保持纯领域模拟与 pygame 表现分离。

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

## 14. Stage02 实际落地

- `domain/encounter.py`：一次 Encounter 的命令槽、回合确认、统一胜负判定与无污染重开；
- `domain/ai.py`：敌人从当前格到可攻击格的 BFS，按稳定 ID 顺序移动并生成公开意图；搜索复杂度为 `O(width × height)`；
- `domain/simulation.py`：仍是 preview/execute 的唯一规则来源，并新增护盾吸收事件；
- `stage02_scenario.py`：仅保存可丢弃的 Stage02 测试战场定义，不是正式 Level 1；
- `stage02_app.py`：将鼠标/键盘输入翻译为 Command，展示状态并按 LogicEvent 播放格子脉冲/事件高亮，不修改战斗事实。

依赖保持 `pygame → Stage02App → Encounter/Command → Simulator → CombatState/LogicEvent`；领域层没有导入 pygame。

## 15. Stage03 实际落地

- `domain/content.py`：关卡、遭遇、敌人生成点和协议插件的不可变定义；
- `infrastructure/config.py`：从 `data/` 读取 JSON，校验必填字段、类型、范围、重复 ID、坏引用和已注册效果类型；
- `domain/level.py`：纯逻辑 `LevelRun`，负责三场遭遇顺序、Reward、玩家生命/Build 继承、敌人隔离、Victory/Defeat/Restart 与重复结算保护；
- `domain/simulation.py`：协议 `effect_type` 在唯一模拟器内部生效；回声改写第三拍，动能、牵引和护盾插件修改对应规则，预演与执行仍共用同一路径；
- `stage03_app.py`：正式菜单、战斗、奖励和结果场景的轻量控制器，只把键鼠输入翻译为命令；
- `presentation/stage03_renderer.py` 与 `audio.py`：消费领域状态和 `LogicEvent`，绘制 HUD、残影、锁定线、单位形状、反馈脉冲并播放可降级的合成提示音；
- `stage03_smoke.py`：通过正式 App/LevelRun API 走通菜单到 Level Clear，再验证干净重启。

依赖保持 `pygame → Stage03App → LevelRun → Encounter → Simulator`。配置层构造类型化定义；表现层不会修改伤害、位置、胜负或协议规则。

## 16. Stage04 实际落地

- `domain/reward.py`：接收注入的 `random.Random`，对配置池做 requirements、conflicts、max_stack 过滤，再执行无放回加权抽取；
- `domain/level.py`：持有 `run_seed`、Build 层数和一次生成后保持不变的候选，选择后才应用并传入下一场 Encounter；Restart 同时重建 RNG 与清空 Build；
- `domain/simulation.py`：8 个有限效果继续在同一模拟器中生效，新增回声护盾、碰撞过载、牵引断锁和盾后反推；
- `infrastructure/config.py`：校验 tags、weight、requirements、conflicts、max_stack、reward_pool 与 reward_count，包括重复、坏引用和自引用；
- `stage03_app.py`：正式运行每局生成新 Seed，`--seed` 为 DEBUG ONLY 固定入口；Reward 场景只提交选择，不直接修改战斗属性；
- Level 1 保持三个 Encounter，不新增敌人或关卡；第一战后仍是冻结的回声/动能/屏障三选一，第二战后从合法池随机三选一深化 Build。

依赖增加为 `LevelRun → RewardPool → random.Random`，随机不进入模拟器，因而不会污染预演/执行一致性。
