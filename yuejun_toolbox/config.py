# -*- coding: utf-8 -*-
"""Resource configuration and declarative tool catalogue; no UI creation."""
import os
from collections import namedtuple

from maya import cmds

ROOT_OPTION = "yuejunToolbox_resourceRoot"
DEFAULT_ROOT = "C:/Yuejun_ToolBox"
OLD_DEFAULT_ROOT = "C:/Yunuo_Issue_01"
ROOT_MIGRATED_OPTION = "yuejunToolbox_rootMigrated31"
Tool = namedtuple("Tool", "key label kind path help")
PROJECT_GROUP = ("项目管理", (
    Tool("project_window", "项目窗口", "ui", "", "打开 Maya 原生项目窗口；先新建或设置工作项目，再导入素材。"),
    Tool("set_project", "设置项目", "ui", "", "打开 Maya 原生设置项目窗口，选择已有的工作项目。"),
    Tool("check_project", "检查当前项目", "ui", "", "检查工作项目规则、场景位置、缺失资源及项目外路径，显示详细报告。"),
))

GROUPS = (
    ("GN 快捷工具", (
        Tool("gn_import", "GN 导入", "gn", "GN_Import", "需要已安装 GN 插件；执行其原生导入流程。"),
        Tool("gn_export", "GN 导出", "gn", "GN_Export", "需要已安装 GN 插件；执行其原生导出流程。"),
    )),
    ("Skin", (
        Tool("cut_uv", "Skin 切 UV", "mel", "Maya_Script/Skin_qieUV.mel", "仅适用于原配 Skin 拓扑；再次执行会再次偏移 UV。"),
        Tool("restore_uv", "Skin 恢复 UV", "mel", "Maya_Script/Skin_huifuUV.mel", "原配模型的反向 UV 偏移及合并；不是通用 UV 备份恢复。"),
        Tool("vray_skin", "V-Ray 设置 · −0.5", "core", "", "需要已加载 V-Ray；在 Skin 网格上设置细分和置换属性。"),
    )),
    ("场景预设", (
        Tool("preset_vray", "打开 V-Ray 预设", "open", "Maya_shader_node/Test_Vray.mb", "直接打开 V-Ray 预设文件，替换当前场景；有未保存修改时先提示。"),
        Tool("preset_arnold", "打开 Arnold 预设", "open", "Maya_shader_node/Arnold/Base_Arnold.ma", "打开素材库中的 Arnold 预设；保留材质、灯光及渲染设置，有未保存修改时先提示。"),
    )),
    ("材质节点", (
        Tool("disp", "Disp", "import", "Maya_shader_node/Disp.ma", "直接导入节点到根命名空间，重名按 Maya 原生规则处理。"),
        Tool("micro", "Micro", "import", "Maya_shader_node/Micro.ma", "直接导入节点到根命名空间，重名按 Maya 原生规则处理。"),
        Tool("disp_black", "Disp Black", "import", "Maya_shader_node/Disp_Black.ma", "直接导入节点到根命名空间，重名按 Maya 原生规则处理。"),
    )),
    ("眼球", (
        Tool("import_eye", "导入 V-Ray 眼球", "import", "Maya_Model/VRay_eye.mb", "将 V-Ray 眼球和可用贴图同步到当前项目后导入。"),
        Tool("import_eye_arnold", "导入 Arnold 眼球", "import", "Maya_Model/Eye_Arnold/Arnold_eye.ma", "将 Arnold 眼球及配套贴图同步到当前项目后导入；需要 Arnold 插件。"),
    )),
    ("目标与生长体", (
        Tool("import_growth", "导入生长体", "legacy_import", "Maya_Model/Skin_shengzhangti.mb", "初版命令：直接导入生长体文件。"),
        Tool("update_growth", "更新生长体", "legacy_mel", "Maya_Script/Skin_chuangjianshengzhangti.Mel", "初版 MEL：使用 Skin UV 对应更新生长体，并清除脚本指定对象的历史。"),
        Tool("rename_target", "BS先点我", "core", "", "初版命令：将当前第一个选中对象重命名为 Mubiao。"),
        Tool("blend_target", "BS切换", "legacy_mel", "Maya_Script/Skin_BSqiehuan.mel", "初版 MEL：创建并应用 BS，清除历史后删除 Mubiao。"),
    )),
    ("工具和帮助", (
        Tool("expression_notes", "XGen 表达式速查", "ui", "", "查看整理好的表达式、操作步骤并复制代码。"),
        Tool("restore_xgen_guides", "恢复 XGen 引导线", "core", "", "修复 xgmMakeGuide 下游的网格与引导线连接；跳过引用、锁定及目标不明确的节点，可撤销。"),
        Tool("clean_unknown_nodes", "清理无效节点", "core", "", "删除本地未锁定的未知节点并移除无用插件依赖；节点删除可撤销，插件依赖记录移除不可撤销。"),
    )),
)
TOOLS = {tool.key: tool for _, group in GROUPS for tool in group}
TOOLS.update({tool.key: tool for tool in PROJECT_GROUP[1]})
GROUP_COLUMNS = {"材质节点": 3, "眼球": 2, "项目管理": 3}
VRAY_TOOLS = {"vray_skin", "preset_vray", "import_eye", "disp", "micro", "disp_black"}
ARNOLD_TOOLS = {"preset_arnold", "import_eye_arnold"}


def visible_groups(vray=False):
    hidden = ARNOLD_TOOLS if vray else VRAY_TOOLS
    return tuple((title, tuple(tool for tool in group if tool.key not in hidden))
                 for title, group in GROUPS if any(tool.key not in hidden for tool in group))


def migrate_preferences():
    """One-time migration of the old default; retain genuinely custom locations."""
    if cmds.optionVar(exists=ROOT_MIGRATED_OPTION):
        return
    if cmds.optionVar(exists=ROOT_OPTION):
        saved = cmds.optionVar(query=ROOT_OPTION)
        if os.path.normcase(os.path.normpath(saved)) == os.path.normcase(os.path.normpath(OLD_DEFAULT_ROOT)):
            cmds.optionVar(stringValue=(ROOT_OPTION, DEFAULT_ROOT))
    cmds.optionVar(intValue=(ROOT_MIGRATED_OPTION, 1))


def resource_root():
    if cmds.optionVar(exists=ROOT_OPTION):
        return os.path.normpath(cmds.optionVar(query=ROOT_OPTION))
    return os.path.normpath(os.environ.get("YUEJUN_TOOLBOX_ROOT", DEFAULT_ROOT))


def set_resource_root(path):
    path = os.path.abspath(os.path.expanduser(path.strip()))
    if not os.path.isdir(path):
        raise ValueError("资源文件夹不存在：{}".format(path))
    if not any(os.path.isdir(os.path.join(path, name)) for name in
               ("Maya_Script", "Maya_Model", "Maya_shader_node", "Maya_Texture", "Maya_Light")):
        raise ValueError("请选择包含 Maya_Script、Maya_Model 等子目录的资源根目录。")
    cmds.optionVar(stringValue=(ROOT_OPTION, path))
    return path


def asset_path(relative):
    root = os.path.realpath(resource_root())
    path = os.path.realpath(os.path.join(root, relative))
    if os.path.commonpath((root, path)) != root:
        raise ValueError("资源路径不能超出资源根目录。")
    stem, extension = os.path.splitext(path)
    if extension.lower() in (".ma", ".mb"):
        # Allow Save As between Maya ASCII/Binary using the same base filename.
        candidates = [candidate for candidate in (path, stem + ".ma", stem + ".mb") if os.path.isfile(candidate)]
        if not candidates:
            old_names = {"VRay_eye": "Eye_Grp", "Arnold_eye": "flippedNormals_eyeKit_Arnold"}
            old = old_names.get(os.path.basename(stem))
            if old:
                candidates = [os.path.join(os.path.dirname(path), old + ext) for ext in (".ma", ".mb")
                              if os.path.isfile(os.path.join(os.path.dirname(path), old + ext))]
        if candidates:
            path = max(candidates, key=lambda candidate: os.stat(candidate).st_mtime_ns)
            path = os.path.realpath(path)
            if os.path.commonpath((root, path)) != root:
                raise ValueError("资源路径不能超出资源根目录。")
    return path
