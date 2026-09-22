Yuejun Toolbox 开发交接说明

当前版本：3.7.14
兼容：Maya 2022 / Python 3.7 / maya.cmds / OpenMaya 2.0

一、从这里继续
本素材库中的 yuejun_toolbox_source 是随包携带的最新开发副本。
先读 AGENTS.md、README.md、docs/DEVELOPMENT.md、CHANGELOG.md、VALIDATION.md。
维护 yuejun_toolbox 模块，不要直接修改 Scripts/YuejunToolbox.py 或 dist 生成脚本。
本次已把 F 盘开发副本的 3.7.13 源码同步到 C:/Yuejun_ToolBox/yuejun_toolbox_source。
今后选定一份工作副本开发，避免 C、F 两份交替修改后互相覆盖。

二、近期改动
3.7.9：MetaHuman 男女 FBX 导入、配套观察贴图与原材质恢复。
3.7.10：观察贴图改为切换按钮；MH切UV/恢复UV 合并，取消 Skin 名称要求，删除 Skin 分组。
3.7.11：修复材质还原后预览材质关联残留；UV 操作忽略软选择，结束或异常时恢复设置。
3.7.12：更新生长体使用选中来源头部，保留来源历史；区域标题改为 MetaHuman。
3.7.13：增加“修复头身接缝”，匹配重合边界点并平均法线，可撤销，不移动或焊接顶点。

三、关键代码位置
config.py：按钮目录和素材路径。
ui.py：界面，与场景逻辑分离。
metahuman.py：模型导入、材质备份/还原、UV 切换、接缝法线。
core.py：生长体更新、BS、场景打开/导入、撤销事务。
project.py / preview.py：项目资源同步与预览保存保护。
其余眼球、VFace、GN、表达式模块保留原有职责。

四、构建和启动
在 yuejun_toolbox_source 目录执行：
  python -m unittest discover -s tests -p "test_*.py" -q
  python scripts/build_single.py
把 dist/YuejunToolbox_3_7_14_Single.py 复制到素材库 Scripts/YuejunToolbox.py。
Maya 的 Python 编辑器运行：
  import runpy
  runpy.run_path(r"C:\Yuejun_ToolBox\Scripts\YuejunToolbox.py", run_name="__main__")
换盘符后修改启动路径，并在工具里重新选择资源目录。
开发模式可运行 yuejun_toolbox_source/launch_maya.py；单文件模式修改源码后必须重新构建、部署并重新执行入口。
升级时同步 __init__.py、ui.py、构建脚本、.gitignore、README 与交接文档版本。

五、行为与限制
场景预设继续“打开”，不恢复已放弃的 3.8.0 合并导入方案。
保留保存保护、模块重载、可撤销操作；不转换素材 ma/mb 格式。
MetaHuman 素材在 Models/Metahuman/Model 与 Texture 下。
材质切换备份随场景保存；旧版残留可重新应用再还原一轮修复。
MH UV 只接受配套头部的面连接和边编号，恢复使用 UV 备份，勿删除备份 UV 集。
生长体来源名称不限，需要配套布局的 map1；四个目标仍按 Hair_Grtuv、Brow_Grtuv、Lash_Grtuv、Beard_Grtuv 唯一识别，并保留 Skin/Hair UV。更新烘焙目标历史，拒绝已有变形器的目标。
接缝修复选择头部与身体，名称/顺序不限；只处理唯一匹配的开放边界，容差 0.01 cm。不修复几何缝隙或贴图色差。
FBX 导入不能完整撤销；不需要的副本删除对应 MetaHuman 组。

六、验证状态
64 项普通 Python 回归测试通过。
8 项独立 Maya 2022 场景测试通过（包含选中来源更新生长体、BS、撤销）。
tests/maya_metahuman.py 已用真实素材在独立 Maya 2022 进程验证导入、材质、UV、软选择、保存重开以及接缝。
接缝样本 92 对顶点约 0.25–0.27 秒，验证旋转/非均匀缩放、位置不变和撤销重做。
生长体更新使用测试平面验证；完整素材外观、最终渲染与 GN 跨机安装仍需人工检查。
Maya 集成脚本必须在独立 MAYA_APP_DIR、独立测试进程执行，不能在工作场景运行。

七、另一台电脑与 GitHub
复制完整素材库，VFace 外部扩展包另行复制并设置路径。Maya/Arnold/V-Ray/GN 按需安装。
默认预览工程位于 Maya 用户目录 projects/Yuejun_Default，不能放在素材库内。
Settings/toolbox.json 及 Maya 偏好可能包含旧电脑路径，请重新设置。
GitHub：https://github.com/Memingqimiao/yuejun-maya-toolbox （公开）
本次发布版本为 3.7.13，包含 3.7.9–3.7.13 的累计改动。远端发布状态以 GitHub main 为准。
本地工作目录含最新源码，但本地提交历史与远端不同；换电脑建议克隆最新 main 后配置素材路径。
本地历史与此前通过 API 上传的远端历史不同，不要直接强制推送，也不要假定 git pull --ff-only 一定成功。
在另一台电脑继续时先备份/提交当前工作改动；需要上传时先检查远端最新状态，基于远端分支同步这份源码，保留远端历史。
商业素材、第三方安装包、Settings、本机日志、凭据均不得提交 Git。

已核实 GitHub main 发布提交：8c6dcfbbc1a56c2d198ecfd6ea444fc40a10b1c0（3.7.13）。

2026-09-22 本地更新：3.7.14（本次发布版本）
C:/Yuejun_ToolBox/yuejun_toolbox_source 为本次维护副本，F 盘旧副本未同步本次新增功能。
新增 mh_fit.py：原 map1 UV 唯一匹配 + 面连接校验；编号修复创建独立新头部，原模型保留，不复制绑定。
MetaHuman 区域选择男女参考，再选择头部，运行“修复顶点编号”或“生成 / 更新配件”。
配件包括双眼、牙齿、睫毛、眼壳、泪线与口腔辅助网格；重复运行更新已有组，覆盖该组手动形状，拒绝已绑定目标。
隐藏参考组是后续计算用的基准，不要手动修改；不生成头发、眉毛、胡须生长体，不自动生成绑定。
原始 UV 必须保留，改动 UV 会拒绝对应。极端形变需要检查眼睑和口腔贴合。
64 项普通回归通过；tests/maya_mh_fit.py 男女素材测试通过：编号反转恢复、配件全局变换、旋转、更新复用、撤销/重做、保存重开、UV 错误拒绝；男性素材另验证眼周局部形变跟随。

本次发布包含 3.7.14 源码与英文目录说明。本地源码目录为 C:/Yuejun_ToolBox/yuejun_toolbox_source；克隆仓库可自行选择目录名。上传状态以 GitHub main 为准。
