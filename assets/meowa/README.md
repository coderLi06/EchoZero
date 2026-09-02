# EchoZero Meowa 素材说明

## 运行素材

- `characters/player.png`：玩家母版；
- `characters/melee.png`：追猎体母版，同时作为突进体的装甲母版；
- `characters/ranged.png`：校验射手母版；
- `characters/warden.png`：最终遭遇相位守卫母版。

四张素材均保留透明通道。运行时以 nearest-neighbor 缩放到战场格内，pygame 继续叠加朝向武器、Enemy Intent、受击闪白、生命条、精英角标与死亡消散。

## 风格参考

`style_reference/ui_component_sheet.png` 是 Meowa 生成的无文字构件板。游戏没有直接拉伸或贴用整张构件板，而是将其非对称切角、窄信号轨与四色语义转换为可响应缩放的 pygame 原生绘制。

原始输出、任务结果与视觉 QA 截图保存在 `artifacts/meowa_generation` 和 `artifacts/meowa_ui_qa`。
