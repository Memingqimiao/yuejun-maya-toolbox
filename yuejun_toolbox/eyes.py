# -*- coding: utf-8 -*-
"""Texture variant selection for the supplied Arnold eye kit; no UI."""
import os
import re
from maya import cmds
from . import config, project, core, preview

COLORS = (("原始配色", "Original"), ("蓝色", "Blue"), ("棕色", "Brown"),
          ("深棕色", "Dark Brown"), ("绿色", "Green"), ("灰色", "Grey"), ("榛色", "Hazel"))
RESOLUTIONS = ("512", "1k", "2k", "4k")
ALBEDO = {"Blue": "blue", "Brown": "brown", "Dark Brown": "darkBrown", "Green": "green", "Grey": "grey", "Hazel": "hazel"}
DISP = {"Blue": "Blue_Grey_Iris", "Grey": "Blue_Grey_Iris", "Brown": "BrownIris", "Dark Brown": "DarkBrownIris", "Green": "GreenIris", "Hazel": "HazelIris"}


def variant(raw, color, resolution):
    if color not in dict(COLORS).values() or resolution not in RESOLUTIONS:
        raise core.ToolError("不支持的眼球颜色或贴图精度。")
    base = os.path.basename(raw.replace("\\", "/"))
    folder = "_512" if resolution == "512" else resolution
    match = re.fullmatch(r"(blue|brown|darkBrown|green|grey|hazel)Iris_Albedo_(512|1k|2k|4k)\.png", base)
    if match:
        original = next(key for key, value in ALBEDO.items() if value == match.group(1))
        chosen = original if color == "Original" else color
        return "irisColors/{}/{}/{}Iris_Albedo_{}.png".format(chosen, folder, ALBEDO[chosen], resolution)
    match = re.fullmatch(r"(Blue_Grey_Iris|BrownIris|DarkBrownIris|GreenIris|HazelIris)_Disp_(512|1k|2k|4k)\.exr", base)
    if match:
        prefix = match.group(1) if color == "Original" else DISP[color]
        return "irisDisp/{}/{}_Disp_{}.exr".format(folder, prefix, resolution)
    match = re.fullmatch(r"(sclera(?:Bright_albedo|Dark_albedo|_bump|_disp|_transmission))_(512|1k|2k|4k)\.(png|exr)", base)
    if match:
        return "sclera/{}/{}_{}.{}".format(folder, match.group(1), resolution, match.group(3))
    return None


def selected_files():
    selected = cmds.ls(selection=True, long=True, objectsOnly=True) or []
    if not selected:
        raise core.ToolError("请先选择要修改的 Arnold 眼球或眼球组。")
    files = set()
    for node in selected:
        if cmds.nodeType(node) == "file":
            files.add(node)
        shapes = cmds.listRelatives(node, allDescendents=True, fullPath=True, type="mesh") or []
        if cmds.nodeType(node) == "mesh":
            shapes.append(node)
        seeds = [node]
        for shape in shapes:
            seeds.extend(cmds.listConnections(shape, type="shadingEngine") or [])
        for seed in seeds:
            files.update(cmds.ls(cmds.listHistory(seed) or [], type="file") or [])
    return files


def apply(color="Original", resolution="2k", nodes=None):
    files = (cmds.ls(nodes, type="file") or []) if nodes is not None else selected_files()
    session = project.SyncSession()
    plan = []
    for node in files:
        raw = cmds.getAttr(node + ".fileTextureName") or ""
        original_plug = node + ".yuejunOriginalEyeTexture"
        original = cmds.getAttr(original_plug) if cmds.objExists(original_plug) else raw
        relative = variant(original if color == "Original" else raw, color, resolution)
        if relative is None:
            continue
        core._editable(node)
        if cmds.getAttr(node + ".fileTextureName", lock=True):
            raise core.ToolError("眼球贴图属性已锁定：" + node)
        source = config.asset_path("Models/Eye_Arnold/sourceimages/" + relative)
        if not os.path.isfile(source):
            raise core.ToolError("找不到眼球贴图：" + source)
        plan.append((node, source, original))
    if not plan:
        raise core.ToolError("没有找到该 Arnold 眼球素材的贴图节点，请选择眼球模型或整组。")
    mapped = [(node, session.resource(source), original) for node, source, original in plan]
    with core.undo_chunk("arnold_eye_settings"):
        for node, path, original in mapped:
            if not cmds.objExists(node + ".yuejunOriginalEyeTexture"):
                cmds.addAttr(node, longName="yuejunOriginalEyeTexture", dataType="string")
                cmds.setAttr(node + ".yuejunOriginalEyeTexture", original, type="string")
            # Keep shader connections, displacement strengths and color spaces unchanged.
            cmds.setAttr(node + ".fileTextureName", path, type="string")
    preview.mark(session)
    return "已更新 {} 个眼球贴图节点（{}）。{}".format(len(mapped), resolution, session.summary())


def import_eye(color="Original", resolution="2k"):
    variant("", color, resolution)  # Validate options before importing any scene nodes.
    path = core.require_file(config.TOOLS["import_eye_arnold"].path)
    core.require_renderer(path)
    session = project.SyncSession(path)
    local = session.copy_file(path, "scene")
    with core.root_namespace(), core.preserve_selection():
        nodes = cmds.file(local, i=True, namespace=":", mergeNamespacesOnClash=True,
                          returnNewNodes=True, executeScriptNodes=False, preserveReferences=True)
        preview.mark(session)
        result = apply(color, resolution, nodes)
        project.localize(session, nodes)
    return "已导入 Arnold 眼球。" + result
