# EchoZero

EchoZero 是一个使用 Python 开发的“动作 Roguelike + 战术因果编排”Demo。正式入口以实时动作战斗为主，危险时刻可冻结时间进入三拍 Tactical Mode；原双关卡策略流程完整保留为 Tutorial / Showcase。

## 项目简介

常态使用 WASD、攻击、闪避和牵引技能实时战斗；按 Q 后，玩家可读取 Behavior Tree 当前准备的 Enemy Intent，编排三条命令并 Preview，再使用同一套模拟规则真实 Execute。详细创新边界见 [INNOVATION.md](INNOVATION.md)。

## 当前开发状态

- Stage 00：方案与交互原型已通过；
- Stage 01：可测试的三槽确定性模拟器与 8×6 pygame 灰盒已完成；
- Stage 02：测试 Encounter 核心战斗闭环已通过；
- Stage 03：Level 1 `校准舱` Vertical Slice 已验收通过；
- Stage 04：随机奖励、两次三选一与三条 Build 路线已验收通过；
- Stage 05：正式 Level 2 `逆相反应堆`、周期规则节点、扫掠体与 Demo Clear 已完成实现验收。
- Stage 06：竞赛级 UI、事件动画、音频、转场、可访问设置与最终反馈打磨已完成实现验收。
- Stage 07：开局独立模拟教学、纯净正式对局、离线场次摘要与 3 名新玩家真人盲测已完成；通关 2/3，Preview / Reverse 理解 3/3，无阻断问题。
- Final Visual Polish：响应式画布、三拍执行轨、因果改写、Preview ghost、Protocol HUD 与 Reward 获得演出已完成；核心规则与内容未变。
- Action Roguelike：Seeded 程序地图、BFS 合法性验证、轻量 Behavior Tree、实时动作战斗、Q Tactical Mode、随机三选一、三 Encounter Run、Boss 与轻量局外解锁已完成。

## 技术栈

- Windows PC
- Python 3.14.2
- pygame-ce 2.5.8
- pytest 9.1.1

## 运行方式

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

### Procedural Run 正式操作

- 主菜单按 Enter 或点击 NEW PROCEDURAL RUN，首次会进入 9 步独立模拟教学；教学依次解释动作、Enemy Intent、Tactical 三拍、Preview 和奖励循环，完成后才创建正式 Run 并显示 Seed；
- 教学中点击空白处或按 Tab / Enter 前进，Shift+Tab 返回，也可“跳过本步 / 全部跳过”，Esc 退出教学；正式战斗右侧可随时“重新进入教学”，重播期间会暂停当前 Run 且不会改变 Seed 或战斗状态；
- Action Run 使用高对比“全息训练舱”界面和 56px 大单元格；玩家、追猎体、突进体、校验射手与相位守卫使用不同轮廓，不需要只靠颜色辨认；
- 每张 Encounter 开场提供 1.65 秒 SYNC WINDOW；Enemy Intent 显示行动倒计时，普通敌人约每 0.96～1.28 秒行动一次，长按移动约每 0.15 秒推进一格；
- 正式 HUD 只显示玩家化的 Enemy Intent；按 `F3` 可切换答辩技术面板，展示 Selector、Sequence、Condition 与当前 PreparedAction，默认关闭；
- WASD 或方向键实时移动；鼠标左键或 Space 向面对方向进行四向基础攻击，不支持斜向；Shift + WASD/方向键闪避；E 沿当前方向牵引；启动和答辩演示前请切换到英文输入法，窗口失焦后点击游戏窗口即可恢复键盘控制，撞墙会显示“前方受阻”；
- 玩家小人会根据逻辑事件播放待机、移动、攻击、闪避、牵引和受击姿态；敌人刀刃、枪口、弹丸与危险区火焰仅负责表现，不改变战斗结算；
- 按 Q 进入 Tactical Mode：1/2/3 选拍，WASD 写入 Move，Space 写入 Push，E 写入 Pull，F 写入 Shield，Backspace 清空，Enter 执行，Q 返回实时战斗；
- 每场结束后用 1/2/3、方向键或鼠标选择“协议 / 技能 / 属性”三选一；构筑继承到下一张程序地图，后续遭遇右栏会持续显示已选强化的名称与当前累计效果；
- 三场中的末场为相位守卫 Boss；死亡或通关后按 Enter 使用新 Seed 重开；
- 完成任意一局后解锁“老兵框架”，后续 Run 起始 CORE +1；最近 Seed 保存在 logs/meta_progress.json 便于复现；
- 主菜单按 F5，或使用 main.py --showcase，进入原 Level 1/2 双关卡策略 Showcase。

### 双关卡 Showcase 操作

- 从主菜单按 `Enter` 或点击“开始校准”；
- 鼠标：点击两个命令槽交换顺序；选槽后点相邻空格设置移动、点相邻敌人设置推击、点玩家设置护盾；右键槽位设为待机；
- 键盘：`1` / `2` / `3` 选槽，`WASD` 设置移动，`E` 牵引最近直线目标，`Q` 设置护盾；
- 首次进入 Level 1 会先启动 9 步模拟教学：单击任意位置或按 `Tab` 前进，也可选择“跳过本步 / 全部跳过”；教学结束后的正式对局不会自动弹出提示，右下角可随时“重新进入教学”；
- 正式对局中 `Enter` 或空格执行，`R` 重新校准，`Esc` 退出；
- 全局可按 `M` 静音，`-` / `+` 调整主音量，`F2` 切换减弱动态；Menu、Battle、Final Encounter 使用不同程序化 BGM，设置会跨 Restart 与 Level 1→2 转场保留；
- 两次奖励界面均可按 `1` / `2` / `3` 或点击卡片选择协议；卡片显示标签与关键规则，顶部显示当前 Build 和本局 Seed；
- 正常启动每局使用新随机 Seed；自动测试可用 `main.py --seed 1` 固定奖励序列。

第一战初始顺序无法解决突进体。将命令调整为“牵引 → 推击 → 移动”，会在敌人执行意图前击杀它；Level 1 完成 Build 后进入 Level 2。逆相规则按 `3→2→1` 执行，绿色相位锚可锁定当前规则，扫掠体会公开多个锁定格，最终击破相位守卫后进入 `CAUSALITY SECURED`。

### 自动验证

```powershell
.\.venv\Scripts\python.exe -m pytest
$env:SDL_VIDEODRIVER = "dummy"
.\.venv\Scripts\python.exe main.py --smoke-test
```

`--smoke-test` 会走完程序 Run 的三场、两次奖励和 Boss 终局，再绘制结果页后退出；`--showcase-smoke-test` 保留原双关卡自动通路。`src/domain` 不导入 pygame；Tactical 的 `preview_turn` 和 `execute_turn` 都调用同一个 `simulate_turn`。

正式运行会在 `logs/session_summary.txt` 覆盖写入不联网、无个人信息的场次摘要，用于记录 Encounter、回合、HP、Build、Retry、Defeat 与引导显示/跳过情况。真人盲测流程见 [Stage07 外部盲测记录](docs/STAGE07_BLIND_TEST.md)，完成数据见 [真人盲测汇总](docs/blind-tests/盲测汇总.md)。

三段 BGM 均为项目原创的 10～12 秒程序化多段循环，不使用或截取其他游戏音乐；纯英文品牌标题使用随项目分发的 SIL OFL 1.1 Orbitron 字体，中文自动回退系统字体；完整来源见 [ASSET_CREDITS.md](ASSET_CREDITS.md)。

Windows onedir 发布包可由已提交的 Spec 重建：

```powershell
.\.venv\Scripts\pyinstaller.exe --noconfirm EchoZero.spec
```

## 项目结构

```text
main.py              程序入口
src/domain/           无 pygame 依赖的战斗规则与模拟器
src/stage03_app.py    正式菜单、关卡、两次奖励与结算控制器
src/action_app.py     程序 Run 的实时输入、Tactical、奖励和终局控制器
src/domain/procedural.py  Seeded 房间/走廊生成与 BFS 合法性验证
src/domain/behavior_tree.py  五类基础节点与三种敌人行为树
src/domain/action_run.py  实时战斗事实、Build 和完整 Run 循环
src/presentation/action_tutorial.py  Action Run 九步独立模拟教学状态
src/presentation/action_art.py  自制代码原生地块、危险区和五类单位轮廓
src/presentation/action_renderer.py  Action 渲染协调、字体缓存与基础绘制
src/presentation/action_renderer_world.py  程序地图、单位、Intent 与 HUD
src/presentation/action_renderer_tutorial.py  Action 九步模拟教学画面
src/presentation/action_renderer_overlays.py  Tactical、Reward、Build 与结果覆盖层
src/presentation/fonts.py  Orbitron 英文标题与中文/正文回退
src/domain/reward.py  可复现的加权候选与合法性过滤
src/presentation/     pygame 正式渲染、事件动效语义和可降级合成音效
src/presentation/battle_view.py  只读战斗视图、玩家文案映射与因果结果信号
src/infrastructure/session_metrics.py  本地无隐私场次摘要
data/                 Level 1、Level 2 与协议插件 JSON 配置
tests/                领域规则和交互测试
任务安排/          项目进度材料
```

## 文档入口

- [项目配置](项目配置.md)
- [创新机制](INNOVATION.md)
- [技术架构](ARCHITECTURE.md)
- [开发路线](ROADMAP.md)
- [任务板](TASKS.md)
- [演示路线](DEMO_PLAN.md)
- [需求 PRD](需求PRD.md)
- [竞品分析](竞品分析.md)
- [每日工作日志](每日工作日志.md)
- [功能测试与初验报告](功能测试与初验报告.md)
- [课程任务验收报告](课程任务验收报告.md)
