# 3.7.8 接续开发说明

本次同步以用户提供的最新版源码仓库为准，结合素材库中的《交接说明.txt》和《目录说明.txt》整理。GitHub 历史保留，当前源码替换旧的 3.7.5 快照。

先读 README.md、DEVELOPMENT.md、CHANGELOG.md 和 VALIDATION.md。维护 yuejun_toolbox 中的模块，禁止单独修改 dist 中的生成脚本。

运行：

```powershell
python -m unittest discover -s tests -p "test_*.py" -q
python scripts/build_single.py
```

将 dist/YuejunToolbox_3_7_8_Single.py 复制到素材库 Scripts/YuejunToolbox.py，或直接在 Maya Python 编辑器运行全文。

本次普通 Python 单元测试 64 项通过，单文件构建通过；未执行真实 Maya 集成测试。BS、GN 安装以及新版路径和渲染预设仍需在独立测试场景验证。

保留 Python 3.7 兼容、预览保存保护、模块重载和撤销支持。场景预设继续使用打开方式。工具表使用现行素材目录名，LEGACY_FOLDERS 仅作兼容回退。默认预览工程必须在素材库之外。

换电脑建议重新克隆最新 main。旧电脑的本地开发历史可能与 GitHub 不同，先备份未提交改动，不要强制推送覆盖远端。素材及 Settings 在各电脑单独配置；代码公开仓库不包含商业素材、第三方安装包和本机日志。
