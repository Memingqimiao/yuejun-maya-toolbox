# 开发与跨电脑同步

稳定基线是 3.7.8（沿用 3.7.1 起的场景预设打开行为）。不要重新引入已放弃的 3.8.0 预设合并导入实验。

## 换电脑

克隆 GitHub 上的公开仓库；推送修改时使用有写入权限的账号。不要把登录令牌写进代码或项目文件。在 IDE 中打开克隆目录，另外复制有权使用的素材库，使用工具内的资源选择器配置路径。

开发前 `git pull --ff-only`，开发时创建分支，例如 `git switch -c codex/improve-xgen-notes`。完成后运行测试与构建，检查 `git diff`，提交并推送，再通过 Pull Request 合并。回到另一台电脑先同步代码；不要用文件夹覆盖方式替代 Git。

## 修改规则

- 保持 Python 3.7 语法及 Maya 2022 API 兼容性。
- `config.py` 定义工具目录；`core.py` / `project.py` / `eyes.py` / `vface.py` / `gn.py` 维护逻辑；`ui.py` 维护主窗口，`vface_ui.py` 维护 VFace 浏览器。
- 第三方插件安装包放在素材库 `Plugins/`，不进入仓库；`gn.py` 按 `GN_ImportExport_v*` 选用版本号最大的一份。
- 工具路径一律写当前目录名；`config.LEGACY_FOLDERS` 只用于识别未迁移的旧素材库，不要反过来把旧名写进工具表。
- 默认预览工程由 `project.default_project_root()` 决定，必须位于素材库之外；素材库只放素材，不放工程输出。
- 笔记写在 `notes_data.py`，速查窗口在 `notes.py`。
- 保留预览保存保护、错误提示、可撤销修改与模块重载能力。
- Maya 素材保持原有 ma / mb 格式；不要为名称规范转换格式。
- 升级版本时同步包版本、UI 标题、构建版本与 README，并更新 .gitignore 中允许提交的发布文件名。
- 新建发布代码由构建脚本生成，单文件必须与维护模块一致。

## 验证

普通测试：`python -m unittest discover -s tests -p "test_*.py" -q`。
构建：`python scripts/build_single.py`。

真实 Maya 验证使用安装目录中的 mayapy.exe，在独立 MAYA_APP_DIR 下运行指定 `tests/maya_*.py`。运行前先阅读脚本：资源集成脚本可能使用默认素材库路径或创建临时项目，必须在测试场景中执行。不要在未保存的工作场景运行集成测试。

## 不进入仓库的内容

贴图、模型、Maya 场景、渲染缓存、原素材库、个人日志、临时目录与历史生成文件不上传。一次性素材迁移脚本及 3.8.0 实验文件仍留在原电脑，但不属于此稳定仓库。
