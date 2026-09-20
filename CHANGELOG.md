# 更新记录

## 3.7.8

- 默认预览工程移出素材库，改用 Maya 用户目录下的 `projects/Yuejun_Default`，可用 `Settings/toolbox.json` 的 `default_project_root` 指定；配置指向素材库内部会被拒绝。
- 素材库内旧的 `Projects/Default` 仍被识别为受管工程，不会触发“项目与素材库互相包含”的报错。
- 清理 Arnold 相关素材里残留的 V-Ray 渲染设置节点（`vraySettings` 及 `vrayformaya` 插件依赖），未加载 V-Ray 时不再报未知节点。
- 项目检查报告中的未知节点提示改为指向“清理无效节点”按钮。

## 3.7.7

- 工具路径直接写当前目录名（RenderPresets / NodePresets / Models / Scripts / Textures / Lights），不再经过旧名映射；旧命名的素材库仍可作为回退被识别。
- 主窗口“资源与工具设置”去掉重复的 VFace 扩展包路径，VFace 目录只在 VFace 浏览器里选择。
- “眼球”和“VFace 素材”合并为一个“素材”分组，眼球颜色与贴图精度仍在该组顶部。
- 素材库整理：删除与新目录完全重复的 Maya_* 旧目录及 3.7.4 迁移备份，Scripts 分出 `_工具箱历史版本` 与 `_未使用的老脚本`。

## 3.7.6

- GN 快捷工具新增“检查 GN 安装”和“安装 GN 插件”。
- 检查会报告素材库安装包、Maya 端文件、userSetup 自启动、当前会话命令及 ZBrush 端状态，不修改任何文件。
- 安装会把 `Plugins/GN_ImportExport_v*` 复制到 Maya 用户脚本目录和 ZBrush 的 `ZStartup/ZPlugs64`，追加自启动（原 userSetup.mel 先备份），并在当前会话直接载入 GN 菜单。
- 存在多个版本时自动选用版本号最大的安装包；ZBrush 目录可用 `Settings/toolbox.json` 的 `zbrush_root` 指定。

## 3.7.5

- BS 工具不再要求 MetaHuman 命名：`BS切换` 改为基于选择，任意两个拓扑一致的模型都能传递造型。
- 同时选中新形状和被修改模型即可一步完成；只选一个则使用 `BS先点我` 标记的形状。
- `BS先点我` 改为记录选中模型（按 UUID，重命名后仍有效），不再把模型改名为 Mubiao。
- 拓扑不一致时先报告两者的点、边、面数并拒绝执行，不改动场景。
- 新增“BS切换后删除新形状模型”勾选框，默认删除；清除历史若带走蒙皮等变形器会在状态栏说明。
- 不再依赖 `Maya_Script/Skin_BSqiehuan.mel`。

## 3.7.4

- 素材库改用 RenderPresets / NodePresets / Models 等新目录名，旧路径自动映射。
- 新增 `Settings/toolbox.json` 配置存储。
- 新增 VFace 素材浏览器，可切换配套 Arnold 预设的头部与贴图。

## 3.7.2

- 以 3.7.1 为基础，保留打开场景预设行为。
- 移除同步 ZB 分组按钮。
- 场景维护更名为工具和帮助。
- 新增包含 12 条笔记的 XGen 表达式速查，支持搜索和复制。

## 3.7.1

- 统一按钮与分组间距，折叠资源设置区。

## 3.7.0

- 项目设置入口与 Arnold / V-Ray 工具显示切换。
- 未设置项目的临时预览与保存保护。
- 眼球文件仅规范名称，保留原格式。
