# EchoZero 素材与版权记录

> 更新日期：2026-09-02。

## 项目自制素材

- Action Run 的玩家小人、Melee 刀刃、Charger 推进轮廓、Ranged 枪械/弹丸、Warden 守卫、地板、墙体和火焰均由 `src/presentation/action_art.py` 在运行时使用 pygame 基础图形绘制；无外部图片来源；
- Menu、Battle、Final 三段背景音乐与全部音效由 `src/presentation/audio.py` 在启动时使用项目自写音序和波形合成；无采样、无截取其他游戏或商业音乐；
- 当前仓库未将互联网图片、第三方游戏音频或来源不明素材放入最终运行路径。

## Meowa 生成素材

- 2026-09-01 使用项目负责人已配置的 Meowa 账户与本地 game-assets skill 生成 EchoZero 几何科幻角色族谱；运行素材位于 `assets/meowa/characters`，包含玩家、近战体、射手和守卫四张透明像素母版；
- 突进体复用近战母版并由 pygame 表现层添加黄色信号识别；第二遭遇后的精英表现使用同一母版增加双线角标，不新增角色、敌人数值或 AI 逻辑；
- Meowa UI 构件板位于 `assets/meowa/style_reference/ui_component_sheet.png`，只作为切角装甲面板、状态条和四色语义图标的视觉参考；正式界面由 pygame 基础图形按窗口逻辑尺寸绘制；
- 角色生成任务：`job_b8a1baa052624ecebd95cfae47eafd2d`；UI 构件任务：`job_4cb482cc51124bec9219375d6ba787ac`。素材使用资格遵循生成账户对应的 Meowa 服务条款。

## Aseprite 兼容动画衍生素材

- 来源：上节已登记的 Meowa 角色 PNG 母版；
- 衍生过程：由项目自写 `tools/build_aseprite_assets.py` 确定性生成像素位移、受击染色、意图角标与扫描线消散；
- 输出：`assets/aseprite/*.png` 与同名 JSON 动画元数据，没有引入第三方游戏素材；
- 构建机未安装 Aseprite，输出格式可直接导入 Aseprite 继续编辑。

## 外部开源视觉资产

- Orbitron SemiBold：用于 `ECHO // ZERO`、`CAUSALITY REWRITTEN` 等纯英文展示标题；中文标题和正文继续使用系统中文字体，避免缺字；
- 作者/版权：Copyright 2018 The Orbitron Project Authors，Reserved Font Name “Orbitron”；
- 来源：[Google Fonts 官方 Orbitron 仓库](https://github.com/googlefonts/orbitron-vf)，字体文件位于 `assets/fonts/orbitron/Orbitron-SemiBold.ttf`；
- 许可证：SIL Open Font License 1.1，完整文本随项目保存为 `assets/fonts/orbitron/OFL.txt`；允许随软件嵌入与再分发，本项目未修改字体或使用保留名称发布衍生字体；
- 加载失败时自动回退到 Bahnschrift / 微软雅黑 / 黑体 / Arial，不影响启动和中文显示。

## 第三方运行库

- pygame-ce：按项目依赖与其自身许可证使用；它是运行库，不是游戏美术或音乐素材。
