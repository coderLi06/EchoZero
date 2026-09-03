# EchoZero Meowa 素材说明

## 运行素材

- `characters/player.png`：玩家母版；
- `characters/melee.png`：追猎体母版，同时作为突进体的装甲母版；
- `characters/ranged.png`：校验射手母版；
- `characters/warden.png`：最终遭遇相位守卫母版。

四张素材均保留透明通道。运行时以 nearest-neighbor 缩放到战场格内，pygame 继续叠加朝向武器、Enemy Intent、受击闪白、生命条、精英角标与死亡消散。

## 风格参考

`style_reference/ui_component_sheet.png` 是 Meowa 生成的无文字构件板。游戏没有直接拉伸或贴用整张构件板，而是将其非对称切角、窄信号轨与四色语义转换为可响应缩放的 pygame 原生绘制。

`industrial_terminal_ui_20260902/.../ui_output.png` 是 2026-09-02 生成的 1536×1152 工业终端最终组件板，任务 ID 为 `job_e42f1b81dcbd4ba1b05048fbeaea2a4c`。正式 Action Run 将其中的暗钢、旧黄铜、军绿屏幕、琥珀状态灯、双层边框和铆钉语言转译为 pygame 原生绘制，不在运行时拉伸整张组件板，也不依赖 Meowa 或网络。

原始输出、任务结果与视觉 QA 截图保存在 `artifacts/meowa_generation` 和 `artifacts/meowa_ui_qa`。
