# Yuejun Maya Toolbox

面向人物制作的 Maya 工具箱。当前稳定版本 **3.7.8**，兼容 Maya 2022 / Python 3.7，使用 maya.cmds 与 OpenMaya 2.0。

## 当前行为

- Maya 项目设置、资源同步及项目外依赖检查。
- 默认 Arnold，可切换显示 V-Ray 工具。
- **场景预设使用打开，不是合并导入**；有未保存修改时提示保存。
- 眼球导入、Arnold 眼球颜色与贴图精度、生长体和 BS 工具。
- **BS 工具按选择工作，不依赖 MetaHuman 命名**：任意两个拓扑一致的模型都能传递造型。
- VFace 素材浏览器，切换配套 Arnold 预设的头部与贴图。
- GN 插件检查与一键安装（Maya 端 + ZBrush 端），安装包放在素材库 `Plugins/`。
- 工具和帮助：XGen 引导线修复、未知节点清理、12 条表达式速查。
- 未设置项目时允许临时预览，设置有效项目后才能保存。

## 在公司电脑使用

1. 克隆此仓库，或在 GitHub 的 Code 菜单下载 ZIP。
2. 单独复制完整素材库（含 Scripts、Models、RenderPresets、NodePresets、Textures、Lights 等目录）。本仓库**不包含第三方模型、贴图、预设或渲染插件**。
3. 在 Maya 2022 Script Editor 的 **Python** 页签运行 [单文件代码](dist/YuejunToolbox_3_7_8_Single.py) 的全部内容，也可保存成 Python 工具架按钮。
4. 展开“资源与工具设置”，选择素材库实际目录。无需使用相同盘符。默认目录为 `C:/Yuejun_ToolBox`，自定义选择会保存到 Maya 偏好。
5. 在项目管理中创建或设置工作项目。素材库与工作项目放在不同目录。未设置项目时，预览会使用 Maya 用户目录下的 `projects/Yuejun_Default`，素材库本身保持精简。

Arnold / V-Ray 与 GN 需要在新电脑单独安装和配置。GN 可用工具箱的“检查 GN 安装”“安装 GN 插件”完成，前提是素材库 `Plugins/GN_ImportExport_v*` 中放有安装包。缺失或仍在原电脑其他磁盘上的贴图不会随代码迁移。请使用“检查当前项目”核对依赖。

## 开发

维护模块位于 `yuejun_toolbox/`；不要直接编辑生成的单文件。

```powershell
python -m unittest discover -s tests -p "test_*.py" -q
python scripts/build_single.py
```

普通 Python 可运行单元测试并构建。`tests/maya_*.py` 是需要真实 Maya / 素材库的人工验证脚本，不由普通 CI 自动运行。

在 Maya 内从本地仓库启动开发版本：

```python
import runpy
runpy.run_path(r"D:/Projects/yuejun-maya-toolbox/launch_maya.py", run_name="__main__")
```

把示例路径改为自己的克隆目录。修改后点击“重载工具”或重新运行启动器。

## 目录

- `yuejun_toolbox/`：配置、核心逻辑、项目同步、眼球工具、UI 和笔记。
- `scripts/build_single.py`：构建可复制的单文件发布版本。
- `tests/`：普通 Python 测试及 Maya 验证脚本。
- `dist/`：当前稳定版本的单文件代码。
- `docs/`：跨电脑开发、资源配置及已知限制。

详见 [开发说明](docs/DEVELOPMENT.md)、[验证说明](VALIDATION.md) 和 [更新记录](CHANGELOG.md)。

## 代码与素材授权

本仓库用于作者维护工具，尚未声明开源许可证；公开可见不代表授予第三方再分发权限。第三方素材、插件和表达式参考内容各自遵循原授权。

素材库布局见 [目录说明](docs/LIBRARY.md)，接续开发见 [交接说明](docs/HANDOFF.md)。
