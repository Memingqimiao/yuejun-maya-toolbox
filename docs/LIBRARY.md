Yuejun Toolbox 目录说明（3.7.14）

先看 交接说明.txt，再开始跨电脑开发。

yuejun_toolbox_source/      最新源码、测试、构建脚本与开发文档；含本地 Git 历史，最新修改尚未提交。
Scripts/         工具箱运行入口 YuejunToolbox.py，以及配套 MEL 等资源脚本。
Models/          眼球、生长体、MetaHuman 等模型。
  Metahuman/Model/    MH_Base_Female.fbx、MH_Base_Male.fbx。
  Metahuman/Texture/  头部、身体、眼睛、牙齿颜色贴图。
RenderPresets/   Arnold / V-Ray 渲染场景预设及配套资源。
NodePresets/     材质节点预设。
Textures/        共用贴图。
Lights/          灯光相关素材。
Plugins/         第三方 GN 等安装包，不进入代码仓库。
Settings/        本机素材配置，换电脑后检查旧路径，不进入代码仓库。

yuejun_toolbox_source内部：
  yuejun_toolbox/        维护模块；MetaHuman 功能在 metahuman.py。
  scripts/build_single.py 构建入口。
  dist/YuejunToolbox_3_7_14_Single.py 当前发布版。
  tests/                单元测试与独立 Maya 集成测试。
  docs/                 开发说明、交接说明和目录说明。
若 dist 或 Scripts 下留有旧版本，属于历史文件，不作为当前入口。
Scripts/_工具箱历史版本、Scripts/_未使用的老脚本（如存在）不参与当前运行。
_Backups（如存在）是原始素材备份，确认不再需要后再自行处理。

默认启动：
  import runpy
  runpy.run_path(r"C:\Yuejun_ToolBox\Scripts\YuejunToolbox.py", run_name="__main__")

素材库不放工作工程或渲染输出。
默认预览工程：Maya 用户目录/projects/Yuejun_Default。
VFace 是外部扩展包，在 VFace 浏览器单独选择路径。
完整素材库用于电脑间携带；上传 GitHub 时只上传源码和文档，不上传素材。

mh_fit.py：头部编号修复与配件适配。运行时在系统临时目录 YuejunToolbox/plugins 生成专用撤销命令，不需手动安装第三方库。
