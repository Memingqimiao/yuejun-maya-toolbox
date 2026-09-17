# 开发与跨电脑同步

稳定基线是 3.7.5，基于用户选定的 3.7.1。不要重新引入已放弃的 3.8.0 预设合并导入实验。

## 换电脑

在 GitHub 登录同一账号后克隆私有仓库。不要把登录令牌写进代码或项目文件。在 IDE 中打开克隆目录，另外复制有权使用的素材库，使用工具内的资源选择器配置路径。

开发前 `git pull --ff-only`，开发时创建分支，例如 `git switch -c codex/improve-xgen-notes`。完成后运行测试与构建，检查 `git diff`，提交并推送，再通过 Pull Request 合并。回到另一台电脑先同步代码；不要用文件夹覆盖方式替代 Git。

## 修改规则

- 保持 Python 3.7 语法及 Maya 2022 API 兼容性。
- `config.py` 定义工具目录；`core.py` / `project.py` / `eyes.py` 维护逻辑；`ui.py` 维护主窗口。
- VFace 核心在 `vface.py`，独立窗口在 `vface_ui.py`。新增模块需同时加入重载顺序和单文件构建器。
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

## 接续开发状态（3.7.5）

- 最新目录设置入口：主窗口只设置工具箱根目录，VFace 目录统一在 VFace 素材窗口设置。
- 已完成 061 / 074 / 115 头部、眼睛、眉毛、睫毛切换及项目内按编号归档；无项目时自动复用 Projects/Default。
- 普通 Python 测试 48 项通过；场景逻辑已在独立 Maya 2022 验证。3.7.5 只删除重复 UI 入口，未改场景逻辑。
- 新电脑先阅读 README.md、docs/LIBRARY.md、docs/VFACE.md 和 VALIDATION.md。代码不包含商业素材、当前工作项目或本机 Settings/toolbox.json。
- 尚待实际 Maya 界面的视觉验收及最终渲染质量验收；独立 Arnold 预览授权不可用，预览有水印。原包未提供虹膜配色贴图，虹膜保留原预设材质。
