# EchoZero Aseprite Animation Source

本目录是现有 Meowa 角色素材的 Aseprite 兼容短帧输出，不包含战斗规则。

- 画布：每帧 `64×64`，水平 Sprite Sheet；
- 锚点：`foot_anchor = (31, 51, 2, 2)`；
- 输出：同名 `.png` 图集与 Aseprite JSON Array 元数据；
- 玩家标签：`idle / move / attack / dodge / hurt`；
- 敌人标签：`idle / prepared / attack / hit / death`；
- 播放：pygame 使用最近邻缩放；Reduce Motion 固定到标签首帧。

本机未安装 Aseprite 时，运行：

```powershell
.\.venv\Scripts\python.exe tools\build_aseprite_assets.py
```

安装 Aseprite 后，可直接打开 PNG，并按同名 JSON 的 `frameTags` 建立标签；再次导出时保持 `64×64` 帧格、水平排列、RGBA8888 和脚底锚点不变。
