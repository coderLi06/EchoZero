# ARCHITECTURE——技术架构

> 状态：Action Roguelike 阶段已完成代码侧实现；原 Stage07 Showcase 保留，继续保持纯领域模拟与 pygame 表现分离。

## 1. 架构目标

支持两关高质量 Showcase、确定性因果预演，以及可复现的程序 Action Run。非目标：通用引擎、ECS 框架、联网、数据库、地图编辑器、脚本语言或复杂连招。

## 2. 依赖方向

```text
pygame 输入 ─→ Scene/Controller ─→ domain Command
                                    ↓
JSON ─→ Config Loader ─→ Registry ─→ Simulator ─→ CombatState
                                    ↓             ↓
                              LogicEvent[] ─→ Renderer/Animation/Audio

Preview: clone(CombatState) ─→ 同一个 Simulator ─→ PreviewResult

Action Run: Seed ─→ ProceduralEncounterGenerator ─→ ActionRun
                                              ↓
实时敌人: BehaviorTree ─→ PreparedAction ─→ Execute + Enemy Intent
战术模式: PreparedAction ─→ EnemyIntent ─→ 现有 Simulator
```

`domain` 不知道窗口、图片、音频和动画；`presentation` 不决定伤害或 AI；`infrastructure` 只负责配置、路径和存档。Showcase 使用确定性的三拍流程；Action Run 用离散网格上的实时冷却推进动作，Q 模式暂停并转入同源三拍模拟。

## 2.1 Action Run 新增职责

- `domain/procedural.py`：Seeded 房间/走廊/障碍/危险/出生点生成，BFS 连通性和距离校验，有限次数失败重试；
- `domain/behavior_tree.py`：BehaviorNode、Selector、Sequence、Condition、Action 与三种敌人树；输出唯一 PreparedAction；
- `domain/action_run.py`：实时动作事实、冷却、Encounter/Reward/Result 流程，以及 Tactical Mode 对 `simulate_turn` 的适配；
- Tactical 候选动作与优先队列也由 `domain/action_run.py` 持有；表现层只选择和排序，领域层把前三项重新编号为 1～3 槽后交给唯一 `simulate_turn`，候补动作不参与结算；
- `presentation/action_renderer.py`：绘制地图、Intent、打击反馈、Tactical Overlay、Reward 和 Run 结果，只读领域状态与事件；
- `action_app.py`：键鼠输入、60 FPS 推进、Seed 展示和场景切换；`Stage03App` 继续作为 Tutorial / Showcase 入口。

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

## 17. Stage05 实际落地

- `CombatState` 增加类型化时间轴规则、规则周期索引和相位锚位置；clone 与 fingerprint 必须包含全部字段；
- `Simulator` 在协议变换后执行统一的时间轴变换，并在回合收尾依据玩家是否占据相位锚决定保持或切换；
- `AI` 继续输出 `EnemyIntent`，扫掠体和相位守卫只是一次生成多个确定目标，不增加第二套攻击结算；
- `LevelRun` 接受显式的初始生命和插件序列，用同一关卡逻辑承载 Level 1 与 Level 2；
- `Stage03App` 只负责两个 `LevelDefinition` 之间的轻量转场与状态传递，不判断 Level 2 战斗规则；
- 配置新增 `rule_cycle`、`rule_nodes` 与第二个关卡 JSON，并保持启动时严格校验。

正式状态流为 `MENU → Level 1 BATTLE/REWARD → TRANSITION → Level 2 BATTLE → DEMO CLEAR/DEFEAT`。Level 2 没有新增 Reward System 或协议；所有逆相、节点和多格意图事件仍由领域层输出，Renderer 只消费状态和事件。

## 18. Stage06 表现层实际落地

- `presentation/effects.py`：把 LogicEvent 映射为短时序、减弱动态、关键震动、音效 cue 与协议可见文案；全部函数只读事件，不持有或修改战斗状态；
- `presentation/stage03_renderer.py`：复用单个离屏画布、字体和文本 Surface，按事件插值位移并绘制命中、护盾、死亡、规则与 Build 反馈；Level 1/2 使用青色/紫色语义，但危险仍用固定红色并辅以斜线与文字；
- `presentation/audio.py`：启动时一次性合成并缓存 20 个短 cue 与 Menu/Battle/Final 三段循环 BGM，使用保留声道、统一主音量和静音；设备不可用时清空声音并静默降级；
- `Stage03App`：只保存选中态、音量、减弱动态、动画起点与已播放事件索引；按键和鼠标仍只翻译为领域命令，表现更新不进入 Simulator；
- 全局设置使用 `M`、`- / +`、`F2`；正式界面不再暴露开发调试入口。

表现依赖保持 `LogicEvent[] → PresentationFrame → Renderer/CueAudio`。命中停顿感是单个事件展示时长变化，不暂停或重复模拟；震动只偏移缓存画布，不改变坐标事实。600 帧无窗口基准平均约 `2.16 ms/frame`，不逐帧读文件、建字体或加载音频。

## 19. Stage07 引导与盲测支持

- `presentation/tutorial.py`：保存开局 9 步模拟教学、当前进度、跳过本步、全部跳过和显式重播状态；它只决定当前展示内容，不修改关卡、命令或模拟状态；
- `presentation/stage03_renderer.py`：教学模式用半透明聚光遮罩和 4 px 方框高亮棋盘、CORE/SHIELD、Intent、三拍槽、Preview、Protocol 与 Execute；正式对局不渲染自动提示，只保留右下角“重新进入教学”；
- `infrastructure/session_metrics.py`：仅记录 Seed、Encounter、回合、HP、Build、Retry、Defeat 与引导状态，并覆盖写入本地文本；不联网、不记录身份或设备隐私；
- `Stage03App`：首次开始 Level 1 时先进入表现层模拟教学；教学激活期间普通左键或 `Tab` 只推进步骤，全部战斗输入被阻断且领域状态不变；完成或跳过后才允许正式输入，Level 2 不再自动插入提示；
- `stage03_smoke.py`：正式 Smoke 路径显式覆盖 Level 1 五个概念、Level 2 顺序/锚点/首次切相以及 Restart。

依赖保持 `Stage03App → ContextualTutorial / SessionMetrics`。二者均位于领域层之外；Preview 和 Execute 仍唯一依赖 `simulate_turn`，教学遮罩、日志和防抖不能改变确定性战斗结果。

## 20. Final Visual Polish 表现强化

- `presentation/battle_view.py`：集中把 Entity/Protocol 内部 ID 解析为类型化配置中的玩家显示名，并保存一次 Execute 的只读来源状态、命令和同源 Preview；
- `presentation/effects.py`：按逻辑 tick 把事件组合为 340～390 ms 的战术拍，使用事件事实构造只读播放状态；Reduce Motion 使用 90 ms 拍并关闭震动、扫描扰动和大位移；
- `Stage03App`：领域结算仍在确认时立即完成；正式 Renderer 存在时只延迟场景切换，依次展示准备、三拍、结果和可选因果改写。自动测试与 Smoke 可绕过等待；
- `Stage03Renderer`：固定 1280×800 逻辑画布，按输出尺寸等比居中缩放并反算鼠标坐标；1600×900、1920×1080 和较低高度窗口均不裁切；
- Preview ghost、Action Slot 交换、CORE/SHIELD 闪色、Encounter 节点脉冲、规则翻转、Protocol HUD 与 Reward 获得动画只消费 BattleView/LogicEvent/UI 时间，不写入领域状态。

依赖保持 `Simulator → LogicEvent/SimulationResult → BattleView/PresentationFrame → Renderer/Audio`。没有第二套 Preview、第二套战斗结算或新的随机源。

## 21. Action Run 新手引导

- `presentation/action_tutorial.py`：保存 9 步独立模拟教学的步骤、进度、返回、跳过本步和全部跳过状态，只描述界面内容，不导入或修改 `ActionRun`；
- `presentation/action_renderer.py`：使用静态模拟战场、非纯颜色的 4 px 聚光框和宽屏说明面板，依次指向 CORE、移动、攻击/闪避/技能、Behavior Tree Intent、Tactical 入口、三拍 Preview 与三选一奖励；
- `ActionApp`：首次 New Run 先启动教学，完成后才调用 `start_new_run`，因此教学不会消费 Seed、生成地图或启动敌人计时；正式战斗重播教学时暂停同一个 Run，退出后原状态继续；
- 正式 Smoke 通过实际 New Run 请求走完教学，再验证三 Encounter、奖励和 Boss 终局；交互测试覆盖返回、跳过、Esc 取消、输入阻断、Seed 不提前消费和重播状态不变。

依赖保持 `ActionApp → ActionTutorial / ActionRenderer` 与 `ActionApp → ActionRun` 两条单向路径。教学层没有 RNG，也不会形成第二套战斗、AI 或 Tactical 规则。

## 22. Action Run 可读性与反应窗口

- `presentation/action_art.py`：集中绘制电路地板、装甲墙、危险标记，以及玩家六边核心、Melee 双刃、Charger 推进箭头、Ranged 准星和 Warden 八角守卫轮廓；全部为项目自制的 pygame 图形，不依赖外部素材或授权；
- `presentation/action_renderer.py`：正式地图单元格由 48px 提升到 56px，地图占据 840×560 主区域，HUD 缩为 324px 信息列；基础表面、地板和正文整体提亮，正文与面板对比度自动测试不低于 4.5:1；
- 教学正文提升到 16px 近白色，遮罩透明度降低，并保留黄色边框与局部聚光双编码；Enemy Intent 增加下一次 Action 秒数，地图开场显示 `SYNC WINDOW`；
- `ActionRun`：每次 Encounter 重置独立 `encounter_elapsed`，首个敌人 Action 延迟 1.65 秒；Melee / Charger / Ranged / Warden 后续间隔分别为 0.96 / 1.18 / 1.28 / 1.08 秒；
- `ActionApp`：长按 WASD 的重复间隔由 105ms 调整为 150ms，单步、闪避和 Tactical 输入规则不变。

表现仍只读取领域事实；单位图形、倒计时和 SYNC 横幅不参与 AI 或伤害结算。节奏测试覆盖安全窗口边界与各类间隔，视觉测试覆盖单元格大小、正文对比度和五种非同形轮廓。

## 23. Action 动作语义、输入与原创音频

- `ActionApp`：WASD 的 `KEYDOWN` 立即调用一次 `move_player`，随后设置 190ms 首次重复等待；保持按键时再以 150ms 间隔连续移动，解决仅依赖 `get_pressed()` 导致短按不移动的问题；
- `ActionApp._consume`：只根据 `LogicEvent` 选择 `move / attack / dodge / skill / hurt` 表现姿态及有限时长；Reduce Motion 会把动作时长限制在 100ms；
- `presentation/action_art.py`：玩家由头、躯干、手臂、腿和能量刃组成；动作进度只改变绘制关节。Melee 根据当前 Action 朝目标举刀，Ranged 在攻击 Action 时沿同一个 Intent 目标绘制枪口和循环弹丸；危险格绘制三簇分相火焰；
- `presentation/action_renderer.py`：奖励类别固定映射为“协议 / 技能 / 属性”，常驻 BUILD 改为“构筑”；
- `presentation/audio.py`：Menu 48 拍、Battle 64 拍、Final 64 拍，分别形成约 12.5s / 12.2s / 10.9s 的原创循环，并叠加原创低音、节拍和高频脉冲；不读取或采样外部游戏音频。

角色动作、武器、弹丸、火焰和音乐均位于表现层。战斗位置、命中、冷却和敌人 Action 继续由领域层决定；素材版权记录集中于 `ASSET_CREDITS.md`。

## 24. Action Final UI Polish

- `presentation/action_renderer.py`：正式 HUD 固定为 CORE/SHIELD、DODGE/SKILL/TACTICAL、玩家化 Enemy Intent 与分类型 Build 四层；`CHASE/STRIKE/SHOOT` 等内部 Action 标签只经展示映射输出中文意图，Behavior Tree 节点仅在 F3 技术面板出现；
- `presentation/action_art.py`：地板使用低对比电路微纹理，墙体降低边缘与铆钉权重，危险区用红色斜纹和火焰双编码；玩家呼吸轮廓、移动/闪避残影、攻击方向、敌人准备脉冲、命中标记和死亡扫描消散均为表现事实；
- `ActionApp`：只保存 F3 面板、CORE flash、移动轨迹、死亡碎片和 680ms Reward 获得反馈的 UI 时间；获得反馈期间暂停实时推进，Reduce Motion 缩短到 320ms；
- `ActionRenderer`：Tactical 使用降亮战场、青色边框、单条扫描线、青/红预测实体与位移箭头；Reward 使用协议紫、技能青、属性绿，并在选择后显示 `ACQUIRED / 获得强化`；
- 响应式继续复用 1280×800 逻辑画布和唯一 `update_viewport_layout()`，初始化后每帧以及 resize/restored/shown/exposed/maximized/focus gained 均从当前 display Surface 幂等刷新。

所有新增状态均位于表现/输入协调层，不导入领域层，也不参与伤害、AI、程序生成、奖励随机或 Tactical 模拟。

## 25. 中文 HUD、Build 可见性与输入焦点

- `presentation/action_renderer.py`：正式右栏以中文呈现核心/护盾、冷却、敌方意图、战术三拍和操作说明；英文只保留低权重系统标签与 F3 技术面板；
- Build 从类型计数改为常驻的“类型 + 强化名称 + 当前累计效果”，协议长说明通过 `effect_type` 映射为等价短句，第二关与 Boss 均能直接确认已选技能是否生效；
- `ActionApp`：WASD 与方向键共用同一方向映射、即时按下和长按重复路径；窗口失焦清除重复计时，恢复/显示/最大化时刷新 viewport 并请求键盘焦点，点击窗口也会恢复焦点；
- 移动受阻继续由领域层返回 `move_blocked`，表现层只显示 520ms“前方受阻”，不改变移动规则或碰撞判定。

依赖仍为 `ActionRun → LogicEvent → ActionApp/ActionRenderer`；输入兼容与文案层没有修改程序地图、Behavior Tree、战斗数值、奖励随机或协议效果。

## 26. 真实键盘事件与输入法边界（2026-08-31）

- `ActionApp._handle_keyboard_event()` 统一消费 pygame `KEYDOWN / KEYUP`，移动方向优先读取 SDL 物理 scancode，再以逻辑 key 兜底；该兼容以 pygame 实际收到键盘事件为前提；
- 长按状态由收到的按下/抬起事件显式维护，不再依赖 `pygame.key.get_pressed()` 的全局翻译结果；最近按下的移动方向进入既有 190ms 首次等待和 150ms 重复节奏；
- 新 Run 和窗口失焦都会清空已按下状态，避免切回窗口后残留移动；方向键、Tactical 三拍输入和原 `_handle_key()` 测试入口保持兼容。

真实 Windows 人工诊断确认：英文输入法下事件、InputState、移动向量、碰撞、玩家坐标和 Renderer 全链正常；中文输入法状态可能不向 pygame 提供可用游戏按键事件。负责人选择答辩前切换英文输入法作为运行要求，不在本阶段接管或关闭系统输入法。

此修复只改变输入适配层，不修改 `ActionRun.move_player()`、碰撞、冷却、地图或任何战斗结算。

## 27. Figma 规范与 Aseprite 兼容短帧（2026-09-01）

- Figma 文件以当前 pygame 常量和 1280×800 逻辑画布为唯一事实，整理 Cover / Foundations、Action、Tactical、Reward / Build 与 Motion Spec；Figma 只承担设计过程、状态对照和答辩说明，不成为运行时依赖；
- `tools/build_aseprite_assets.py` 从已批准的 Meowa 64px 母版确定性生成水平 PNG 图集与 Aseprite JSON 标签，统一脚底锚点；本机无需安装 Aseprite即可重建，安装后可继续逐帧编辑；
- `presentation/action_assets.py` 优先读取图集的 `frameTags`，按姿态和进度返回帧；图集缺失时回退静态 Meowa 素材，Charger 继续复用 Melee 母版；
- `ActionApp` 已有 LogicEvent 姿态仍是唯一动画输入；Renderer 只选择 Idle / Move / Attack / Dodge / Hurt 或 Prepared / Hit 帧，Reduce Motion 固定主帧；
- Tactical 的“因果链”只把现有命令序列翻译为玩家文案，不参与 Protocol、伤害、意图取消、Preview 或 Execute。

依赖保持 `LogicEvent / PreparedAction / Command[] → ActionApp 姿态 → ActionSpriteLibrary → Renderer`；领域层不导入 pygame，程序地图、BFS、行为树、奖励和随机规则未修改。

## 28. 真人盲测后的最小可读性闭环（2026-09-02）

- `presentation/action_renderer.py`：地图敌人与右栏意图使用同一组 `E1–E4` 文本编号，避免玩家只能依赖颜色或位置猜测对应关系；
- Action 教学和常驻操作提示明确攻击只沿面对方向的上、下、左、右四向生效，不支持斜向；
- `presentation/stage03_renderer.py`：Level 2 持续显示相位锚的触发条件和效果，激活后明确说明“下一回合保持当前执行顺序”；
- 三项调整均来自 3 份真人盲测中的共性可读性问题，没有根据单份意见修改 Boss 数值、生命、护盾、掉落或关卡规则。

这些变化只增加玩家可见的文本与编号映射，仍由 Renderer 读取现有敌人、意图和规则节点事实；领域层、程序生成、行为树、Preview 与 Execute 保持不变。

## 29. 表现层拆分与历史回归收敛（2026-09-02）

- 原 1032 行 `presentation/action_renderer.py` 按职责拆为协调/基础绘制、世界与 HUD、独立教学、Tactical/Reward/Result 覆盖层及共享布局常量；入口文件 228 行，最大子模块 345 行；
- 拆分采用无状态表现 Mixin，只复用 `ActionRenderer` 的 Surface、字体缓存和只读 Sprite Library，不新增领域状态、事件或第二套渲染入口；
- `stage02_app.py` 删除 319 行已退役 pygame UI，缩为历史 Stage02 换序、同源预演和重开测试所需的轻量回归夹具；正式入口从未依赖该文件；
- Action Run 是正式程序化动作入口，Showcase 是两关机制答辩入口；二者仍服务不同验收路径，但 Tactical Preview / Execute、Command、CombatState 与 LogicEvent 继续共享领域实现；
- `presentation/fonts.py` 统一 Action / Showcase 字体选择：纯英文展示标题优先使用项目内 Orbitron，中文和正文走系统字体回退。

本轮只调整表现模块和历史测试夹具，不修改战斗、AI、程序地图、奖励、Seed 或结算规则。

## 30. 远近程攻击与相位守卫十字锁定（2026-09-02）

- `domain/action_run.py` 以 `AttackMode` 保存玩家当前攻击模式；近战与远程共用同一伤害增益入口，远程仅在最终伤害阶段执行 50% 下取整并保证至少 1 点；
- 远程射线只沿玩家朝向扫描 3 格，越界或墙体立即终止，并对遇到的第一个存活敌人结算；领域层返回 `ranged_fired` / `damage` 事件，表现层只绘制弹道与受击姿态；
- `PreparedAction.target_positions` 表达多格公开锁定。相位守卫特殊攻击生成中心加四个正交相邻格，实时 Intent、Tactical 投影与执行都读取同一目标集合；
- 第三场生成器固定相位守卫 12 HP；行为树固定其普通伤害 3、特殊伤害 4，半血后只缩短特殊攻击冷却；
- `presentation` 仅消费攻击模式、Boss 状态和事件，绘制工业终端面板、模式提示、Boss 条和十字危险格，不反向修改规则。

依赖仍保持 `Input → ActionRun/BehaviorTree → LogicEvent/PreparedAction → ActionApp/Renderer`，`src/domain` 不导入 pygame。

## 31. Tactical 动态战损摘要（2026-09-03）

- `ActionRun.enemy_numbers` 在每次 Encounter 构建时按生成顺序固化 `E1–E5`，地图徽章、实时 Intent、Preview ghost 与战损摘要均调用 `enemy_number()`，敌人死亡不会导致剩余编号漂移；
- `ActionRun.tactical_preview_summary` 每次读取当前前三拍时调用既有 `preview_turn`，比较真实当前状态与预演状态，生成玩家 HP 前后值及实际受伤敌人的结构化 `TacticalEnemyDelta`；
- 表现层只将摘要绘制为玩家固定行和最多三条敌人战损行；没有敌人受伤时显示空状态，不根据动画或 UI 自行推算伤害；
- 排序操作仍只更新 `tactical_actions` 与前三条 `commands`，下一帧读取同源摘要，因此预演变化不需要额外缓存或失效管理。

依赖保持 `TacticalAction[] → Command[3] → preview_turn → TacticalPreviewSummary → Renderer`，Execute 仍调用同一个模拟器。

## 32. Showcase 连续回合命令续接（2026-09-03）

- `Encounter.confirm_turn()` 在战斗仍为 `ONGOING` 时不再无条件把三槽清空：无实体引用的移动、推击、护盾等命令保留原槽位；
- 若牵引命令指向本回合已死亡的敌人，领域层根据下一轮已重新定位的状态，优先生成朝最近存活敌人的合法移动；若敌人已相邻则生成对应方向的推击；只有玩家四周均不可达时才回退为待机；
- 建议命令仍是普通 `Command`，玩家可以继续换序、改写或右键清空；Preview 与 Execute 不增加特殊分支，继续共用 `simulate_turn`；
- `Stage03App` 只更新回合完成提示，不在表现层计算路径、伤害或目标有效性。

依赖保持 `execute_turn → prepare_enemy_turn → next Command[3] → preview_turn`，没有新增随机源或第二套结算。
