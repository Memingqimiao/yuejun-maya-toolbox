# Yuejun Maya Toolbox

面向人物制作的 Maya 工具箱。当前稳定版本 **3.7.5**，兼容 Maya 2022 / Python 3.7，使用 maya.cmds 与 OpenMaya 2.0。

## 当前行为

- Maya 项目设置、资源同步及项目外依赖检查。
- 默认 Arnold，可切换显示 V-Ray 工具。
- Arnold VFace 头部、眼睛、眉毛、睫毛及贴图切换，按需同步资源、复用隐藏网格缓存；详见 [VFace 使用说明](docs/VFACE.md)。
- **场景预设使用打开，不是合并导入**；有未保存修改时提示保存。
- 眼球导入、Arnold 眼球颜色与贴图精度、生长体和 BS 工具。
- 工具和帮助：XGen 引导线修复、未知节点清理、12 条表达式速查。
- 打开渲染预设或切换 VFace 时，无有效项目则自动创建/复用素材库下的 `Projects/Default`。其他导入操作仍保留临时预览保护。

## 在公司电脑使用

1. 克隆此仓库，或在 GitHub 的 Code 菜单下载 ZIP。
2. 单独复制完整素材库（含 RenderPresets、NodePresets、Models、Scripts 等目录）。本仓库**不包含第三方模型、贴图、预设或渲染插件**。
3. 在 Maya 2022 Script Editor 的 **Python** 页签运行 [单文件代码](dist/YuejunToolbox_3_7_5_Single.py) 的全部内容，也可保存成 Python 工具架按钮。
4. 展开“资源与工具设置”，选择素材库实际目录。无需使用相同盘符。默认目录为 `C:/Yuejun_ToolBox`，自定义选择会保存到 Maya 偏好。
5. 在“VFace 素材”窗口选择素材目录。主要设置写入素材库的 `Settings/toolbox.json`。
6. 可设置自己的工作项目；未设置时，打开预设或切换 VFace 会自动使用 `Projects/Default`。

Arnold / V-Ray 与 GN 需要在新电脑单独安装和配置。缺失或仍在原电脑其他磁盘上的贴图不会随代码迁移。请使用“检查当前项目”核对依赖。

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

素材目录布局及默认项目规则详见 [素材库说明](docs/LIBRARY.md)。

详见 [开发说明](docs/DEVELOPMENT.md)、[验证说明](VALIDATION.md) 和 [更新记录](CHANGELOG.md)。

## 代码与素材授权

本仓库用于作者维护工具，尚未声明开源许可证；私有上传不代表授予第三方再分发权限。第三方素材、插件和表达式参考内容各自遵循原授权。
