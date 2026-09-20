# -*- coding: utf-8 -*-
"""Resource configuration and declarative tool catalogue; no UI creation."""
import os
import json
import tempfile
from collections import namedtuple

from maya import cmds

ROOT_OPTION = "yuejunToolbox_resourceRoot"
DEFAULT_ROOT = "C:/Yuejun_ToolBox"
OLD_DEFAULT_ROOT = "C:/Yunuo_Issue_01"
# Tool paths use the current folder names. Older libraries that still carry the
# pre-3.7.4 names are resolved through these pairs by asset_path.
LEGACY_FOLDERS = (
    ("RenderPresets/Arnold", "Maya_shader_node/Arnold"),
    ("RenderPresets/VRay/Test_Vray.mb", "Maya_shader_node/Test_Vray.mb"),
    ("NodePresets", "Maya_shader_node"),
    ("Models", "Maya_Model"), ("Scripts", "Maya_Script"),
    ("Textures", "Maya_Texture"), ("Lights", "Maya_Light"),
)
REQUIRED_FOLDERS = ("RenderPresets", "NodePresets", "Models", "Scripts", "Textures", "Lights")
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
        Tool("gn_check", "检查 GN 安装", "gn_manage", "", "检查素材库安装包、Maya 端文件、userSetup 自启动及 ZBrush 端，显示详细报告；不修改任何文件。"),
        Tool("gn_install", "安装 GN 插件", "gn_manage", "", "把素材库 Plugins 中的 GN 安装包复制到 Maya 用户脚本目录和 ZBrush 插件目录，写入自启动并在当前会话载入菜单。"),
    )),
    ("场景预设", (
        Tool("preset_vray", "打开 V-Ray 预设", "open", "RenderPresets/VRay/Test_Vray.mb", "直接打开 V-Ray 预设文件，替换当前场景；有未保存修改时先提示。"),
        Tool("preset_arnold", "打开 Arnold 预设", "open", "RenderPresets/Arnold/Base_Arnold.ma", "打开素材库中的 Arnold 预设；保留材质、灯光及渲染设置，有未保存修改时先提示。"),
    )),
    ("素材", (
        Tool("import_eye", "导入 V-Ray 眼球", "import", "Models/VRay_eye.mb", "将 V-Ray 眼球和可用贴图同步到当前项目后导入。"),
        Tool("import_eye_arnold", "导入 Arnold 眼球", "import", "Models/Eye_Arnold/Arnold_eye.ma", "将 Arnold 眼球及配套贴图同步到当前项目后导入；需要 Arnold 插件。"),
        Tool("vface_browser", "VFace 头部与贴图…", "ui", "", "打开 VFace 素材浏览器，在其中选择素材目录并切换配套 Arnold 预设的头部及贴图。"),
        Tool("mh_female", "导入 MetaHuman 女", "mh_import", "Models/Metahuman/Model/MH_Base_Female.fbx", "导入女性基础模型，保留原材质与 UV。"),
        Tool("mh_male", "导入 MetaHuman 男", "mh_import", "Models/Metahuman/Model/MH_Base_Male.fbx", "导入男性基础模型，保留原材质与 UV。"),
        Tool("mh_apply", "观察贴图 / 还原", "mh", "", "选中 MetaHuman 组或子网格，点击应用观察贴图，再次点击还原原材质。"),
        Tool("mh_uv", "MH切UV / 恢复UV", "mh", "", "选择符合配套 MetaHuman 拓扑的头部；首次切 UV，再次精确还原，不要求名称。"),
        Tool("mh_seams", "修复头身接缝", "mh", "", "同时选中头部和身体，平均重合边界点法线；不移动顶点、不焊接，可撤销。"),
    )),
    ("材质节点", (
        Tool("disp", "Disp", "import", "NodePresets/Disp.ma", "直接导入节点到根命名空间，重名按 Maya 原生规则处理。"),
        Tool("micro", "Micro", "import", "NodePresets/Micro.ma", "直接导入节点到根命名空间，重名按 Maya 原生规则处理。"),
        Tool("disp_black", "Disp Black", "import", "NodePresets/Disp_Black.ma", "直接导入节点到根命名空间，重名按 Maya 原生规则处理。"),
    )),
    ("目标与生长体", (
        Tool("import_growth", "导入生长体", "legacy_import", "Models/Skin_shengzhangti.mb", "初版命令：直接导入生长体文件。"),
        Tool("update_growth", "更新生长体", "core", "", "选中头部网格按 map1 UV 更新配套生长体；来源名称不限，保留来源历史，生长体结果烘焙。"),
        Tool("rename_target", "BS先点我", "core", "", "选中新形状模型，记住它作为 BS 目标形状；不改名、不修改场景。"),
        Tool("blend_target", "BS切换", "core", "", "把目标形状的造型传到被修改模型上并烘焙历史。同时选中两个模型（先新形状后被改模型）即可一步完成；只选一个则使用上一次标记的目标形状。要求两者拓扑完全一致。"),
    )),
    ("工具和帮助", (
        Tool("expression_notes", "XGen 表达式速查", "ui", "", "查看整理好的表达式、操作步骤并复制代码。"),
        Tool("restore_xgen_guides", "恢复 XGen 引导线", "core", "", "修复 xgmMakeGuide 下游的网格与引导线连接；跳过引用、锁定及目标不明确的节点，可撤销。"),
        Tool("clean_unknown_nodes", "清理无效节点", "core", "", "删除本地未锁定的未知节点并移除无用插件依赖；节点删除可撤销，插件依赖记录移除不可撤销。"),
    )),
)
TOOLS = {tool.key: tool for _, group in GROUPS for tool in group}
TOOLS.update({tool.key: tool for tool in PROJECT_GROUP[1]})
GROUP_COLUMNS = {"材质节点": 3, "素材": 2, "项目管理": 3}
VRAY_TOOLS = { "preset_vray", "import_eye", "disp", "micro", "disp_black"}
ARNOLD_TOOLS = {"preset_arnold", "import_eye_arnold", "vface_browser"}


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
    accepted = REQUIRED_FOLDERS + tuple(legacy for _, legacy in LEGACY_FOLDERS if "/" not in legacy)
    if not any(os.path.isdir(os.path.join(path, name)) for name in accepted):
        raise ValueError("请选择包含 RenderPresets、NodePresets、Models 等子目录的资源根目录。")
    cmds.optionVar(stringValue=(ROOT_OPTION, path))
    return path


def asset_path(relative):
    root = os.path.realpath(resource_root())
    relative = resolve_folder(root, relative)
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


def resolve_folder(root, relative):
    """Keep the current folder name; fall back to the pre-3.7.4 one if it is missing."""
    relative = relative.replace("\\", "/")
    if os.path.exists(os.path.join(root, relative)):
        return relative
    for current, legacy in LEGACY_FOLDERS:
        if relative == current or relative.startswith(current + "/"):
            candidate = legacy + relative[len(current):]
            if os.path.exists(os.path.join(root, candidate)):
                return candidate
    return relative


def current_path(relative):
    """Rewrite a pre-3.7.4 folder name to the current one, for naming inside projects."""
    relative = relative.replace("\\", "/")
    for current, legacy in LEGACY_FOLDERS:
        if relative == legacy or relative.startswith(legacy + "/"):
            return current + relative[len(legacy):]
    return relative


def settings():
    path = os.path.join(resource_root(), "Settings", "toolbox.json")
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError("Settings/toolbox.json 必须是 JSON 对象。")
    return data


def set_setting(key, value):
    data = settings()
    data[key] = value
    folder = os.path.join(resource_root(), "Settings")
    os.makedirs(folder, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=folder, delete=False) as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        temp = stream.name
    try:
        os.replace(temp, os.path.join(folder, "toolbox.json"))
    finally:
        if os.path.isfile(temp):
            os.remove(temp)


def vface_root():
    saved = settings().get("vface_root", "")
    if saved:
        return saved
    key = "yuejunToolbox_vfaceRoot"
    return cmds.optionVar(query=key) if cmds.optionVar(exists=key) else ""


def set_vface_root(path):
    path = os.path.abspath(os.path.expanduser(path.strip()))
    if not os.path.isdir(path):
        raise ValueError("VFace 扩展包目录不存在：" + path)
    set_setting("vface_root", path)
    cmds.optionVar(stringValue=("yuejunToolbox_vfaceRoot", path))
    return path
