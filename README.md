# EchoZero

EchoZero 是一个使用 Python 开发的 Roguelike 策略游戏 Demo，面向程序设计实训竞赛展示，重点围绕创新玩法、策略构筑和高完成度双关卡体验进行开发。

## 项目简介

当前核心机制为“三拍命令链 + 因果预演”：玩家编排三条命令，预先观察确定性结果，再使用同一套模拟规则真实执行。详细创新边界见 [INNOVATION.md](INNOVATION.md)。

## 当前开发状态

- Stage 00：方案与交互原型已通过；
- Stage 01：可测试的三槽确定性模拟器与 8×6 pygame 灰盒已完成；
- Stage 02：测试 Encounter 核心战斗闭环已通过；
- Stage 03：Level 1 `校准舱` Vertical Slice 已验收通过；
- Stage 04：随机奖励、两次三选一与三条 Build 路线已验收通过；
- Stage 05：正式 Level 2 `逆相反应堆`、周期规则节点、扫掠体与 Demo Clear 已完成实现验收。
- Stage 06：竞赛级 UI、事件动画、音频、转场、可访问设置与最终反馈打磨已完成实现验收。
- Stage 07：就地新手引导、Level 2 规则教学、离线场次摘要与盲测模板已完成代码侧实现；真人外部盲测待执行。

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

### 双关卡正式操作

- 从主菜单按 `Enter` 或点击“开始校准”；
- 鼠标：点击两个命令槽交换顺序；选槽后点相邻空格设置移动、点相邻敌人设置推击、点玩家设置护盾；右键槽位设为待机；
- 键盘：`1` / `2` / `3` 选槽，`WASD` 设置移动，`E` 牵引最近直线目标，`Q` 设置护盾；
- `Enter` 或空格执行，`R` 重启 Level 1，`F3` 切换调试信息，`Esc` 退出；引导可用 `Tab` 快速继续、`F1` 一次跳过且本局不再打断；
- 全局可按 `M` 静音，`-` / `+` 调整主音量，`F2` 切换减弱动态；Menu、Battle、Final Encounter 使用不同程序化 BGM，设置会跨 Restart 与 Level 1→2 转场保留；
- 两次奖励界面均可按 `1` / `2` / `3` 或点击卡片选择协议；卡片显示标签与关键规则，顶部显示当前 Build 和本局 Seed；
- 正常启动每局使用新随机 Seed；测试或演示可用 `main.py --seed 1` 固定奖励序列（DEBUG ONLY）。

第一战初始顺序无法解决突进体。将命令调整为“牵引 → 推击 → 移动”，会在敌人执行意图前击杀它；Level 1 完成 Build 后进入 Level 2。逆相规则按 `3→2→1` 执行，绿色相位锚可锁定当前规则，扫掠体会公开多个锁定格，最终击破相位守卫后进入 `DEMO CLEAR`。

### 自动验证

```powershell
.\.venv\Scripts\python.exe -m pytest
$env:SDL_VIDEODRIVER = "dummy"
.\.venv\Scripts\python.exe main.py --smoke-test
```

`--smoke-test` 会通过正式 App/LevelRun/Encounter 接口走完两关、两次奖励、转场、最终战、`DEMO CLEAR` 与 Restart，再绘制界面后退出。`src/domain` 不导入 pygame；`preview_turn` 和 `execute_turn` 都调用同一个 `simulate_turn`。

正式运行会在 `logs/session_summary.txt` 覆盖写入不联网、无个人信息的场次摘要，用于记录 Encounter、回合、HP、Build、Retry、Defeat 与引导显示/跳过情况。真人盲测流程见 [Stage07 外部盲测记录](docs/STAGE07_BLIND_TEST.md)。

## 项目结构

```text
main.py              程序入口
src/domain/           无 pygame 依赖的战斗规则与模拟器
src/stage03_app.py    正式菜单、关卡、两次奖励与结算控制器
src/domain/reward.py  可复现的加权候选与合法性过滤
src/presentation/     pygame 正式渲染、事件动效语义和可降级合成音效
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
