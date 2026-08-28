# EchoZero

EchoZero 是一个使用 Python 开发的 Roguelike 策略游戏 Demo，面向程序设计实训竞赛展示，重点围绕创新玩法、策略构筑和高完成度双关卡体验进行开发。

## 项目简介

当前核心机制为“三拍命令链 + 因果预演”：玩家编排三条命令，预先观察确定性结果，再使用同一套模拟规则真实执行。详细创新边界见 [INNOVATION.md](INNOVATION.md)。

## 当前开发状态

- Stage 00：方案与交互原型已通过；
- Stage 01：可测试的三槽确定性模拟器与 8×6 pygame 灰盒已完成；
- Stage 02：尚未开始，等待阶段门确认。

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

### 灰盒操作

- 鼠标：先点一个命令槽，再点另一个槽，两者交换；
- 键盘：`1` / `2` / `3` 选槽，方向键换序；
- `Enter` 或空格执行，`R` 重置，`Esc` 退出。

初始顺序会让玩家踏入敌人锁定格并受伤。将命令调整为“牵引 → 推击 → 移动”，会在敌人执行意图前击杀它。

### 自动验证

```powershell
.\.venv\Scripts\python.exe -m pytest
$env:SDL_VIDEODRIVER = "dummy"
.\.venv\Scripts\python.exe main.py --smoke-test
```

`src/domain` 不导入 pygame。`preview_turn` 和 `execute_turn` 都调用同一个 `simulate_turn`，执行后界面会对比两者的终态指纹。

## 项目结构

```text
main.py              程序入口
src/domain/           无 pygame 依赖的战斗规则与模拟器
src/app.py            pygame 灰盒输入与绘制
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
