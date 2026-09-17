# -*- coding: utf-8 -*-
"""Calibrated VFace head switching for the supplied Arnold template; no UI."""
import hashlib
import json
import os

from maya import cmds
from . import core, project, preview, config

ROOT_OPTION = "yuejunToolbox_vfaceRoot"
TAG = "yuejunVFaceSource"
UTILITY = "texturingxyz_vface_specular_roughness_setup_shader_XYZ_utility_lin_srgb_6"
FILES = {
    "geometry": "geos/XYZ_headEyesOpen_GEO.obj",
    "albedo": "maps/XYZ_albedo_lin_srgb.1001.exr",
    "displacement": "maps/XYZ_dispCalibrated_mid0_raw.1001.exr",
    "utility": "maps/XYZ_utility_lin_srgb.1001.exr",
}
EXTRAS = tuple(("eyes", "XYZ_{}_{}_GEO".format(part, side), "Eyes")
               for part in ("iris", "sclera", "tearDuct", "tearLine") for side in ("left", "right")) + (
    ("groom", "XYZ_eyelashes_up_GEO", "Eyelashes"),
    ("groom", "XYZ_eyelashes_down_GEO", "Eyelashes"),
    ("groom", "XYZ_eyebrows_primary_GEO", "Eyebrows"),
    ("groom", "XYZ_eyebrows_secondary_GEO", "Eyebrows"))


def extra_assets(folder):
    result = {name: os.path.join(folder, "03_extra", part, "geos", name + ".obj")
              for part, name, group in EXTRAS}
    for side in ("left", "right"):
        for kind, filename in (("albedo", "XYZ_albedo_{}_angular_lin_srgb.exr"),
                               ("displacement", "XYZ_dispCalibrated_{}_angular_mid0_raw.exr")):
            result[side + "_" + kind] = os.path.join(folder, "03_extra", "eyes", "maps", "sclera", filename.format(side))
    missing = [path for path in result.values() if not os.path.isfile(path)]
    if missing:
        raise core.ToolError("缺少 VFace 眼睛或毛发配套资源，未切换：\n" + "\n".join(missing))
    return result


def assets(folder):
    head = os.path.join(os.path.abspath(folder), "01_head")
    result = {key: os.path.join(head, path) for key, path in FILES.items()}
    missing = [path for path in result.values() if not os.path.isfile(path)]
    if missing:
        raise core.ToolError("VFace 素材不完整：\n" + "\n".join(missing))
    return result


def discover(root):
    """Accept a single identity or its immediate parent; do not scan all drives."""
    if not os.path.isdir(root):
        raise core.ToolError("请选择 VFace 素材总目录，或单个编号目录。")
    candidates = [root] if os.path.isdir(os.path.join(root, "01_head")) else [
        os.path.join(root, name) for name in sorted(os.listdir(root))
        if os.path.isdir(os.path.join(root, name, "01_head"))]
    result = []
    for folder in candidates:
        try:
            assets(folder)
        except core.ToolError:
            continue
        result.append((os.path.basename(os.path.normpath(folder)), os.path.abspath(folder)))
    return result


def linear_space():
    spaces = cmds.colorManagementPrefs(query=True, inputSpaceNames=True)
    for name in ("Utility - Linear - sRGB", "scene-linear Rec 709/sRGB", "linear sRGB"):
        if name in spaces:
            return name
    raise core.ToolError("当前色彩配置没有线性 sRGB 输入空间；请检查 Maya 色彩管理。")


def validate_scene():
    if cmds.getAttr("defaultRenderGlobals.currentRenderer") != "arnold":
        raise core.ToolError("请先使用工具打开 Arnold 场景预设。")
    matches = set()
    for name in ("XYZ_headEyesOpen_GEO_Mesh", "XYZ_headEyesOpen_GEO"):
        matches.update(cmds.ls(name, long=True, type="transform") or [])
    if len(matches) != 1:
        raise core.ToolError("需要唯一的 VFace 头部模型，请先打开配套 Arnold 预设。")
    target, shape, mesh = core.mesh(next(iter(matches)), editable=True)
    if cmds.listConnections(shape + ".inMesh", source=True, destination=False):
        raise core.ToolError("头部有建模或变形历史，请在独立的预设场景切换。")
    for attr in ("outMesh", "worldMesh"):
        if cmds.listConnections(shape + "." + attr, source=False, destination=True):
            raise core.ToolError("头部被其他节点使用（例如 XGen 或变形器），请先在独立预设场景切换。")
    groups = set(cmds.listConnections(shape, type="shadingEngine") or [])
    if groups != {"aiStandardSurface1SG"}:
        raise core.ToolError("头部材质分配与配套预设不同，未进行切换。")
    for node in ("file2", "file4", UTILITY, "displacementShader1", "Skin_Mat"):
        if not cmds.objExists(node):
            raise core.ToolError("缺少配套预设节点：" + node)
        core._editable(node)
    if not cmds.isConnected("file4.outColor", "Skin_Mat.subsurfaceColor"):
        raise core.ToolError("皮肤颜色网络已改变，未进行切换。")
    if not cmds.isConnected("displacementShader1.displacement", "aiStandardSurface1SG.displacementShader"):
        raise core.ToolError("皮肤置换网络已改变，未进行切换。")
    if UTILITY not in (cmds.listHistory("Skin_Mat") or []):
        raise core.ToolError("皮肤 utility 网络已改变，未进行切换。")
    for plug in [shape + ".intermediateObject", "displacementShader1.displacement"] + [
            node + "." + attr for node in ("file2", "file4", UTILITY)
            for attr in ("fileTextureName", "colorSpace", "ignoreColorSpaceFileRules")]:
        if cmds.getAttr(plug, lock=True):
            raise core.ToolError("属性已锁定：" + plug)
    return target, shape, mesh.numVertices, mesh.numPolygons


def _stage_geometry(path, target, key, counts=None, label="VFace"):
    """Import to an intermediate shape before the undoable visible-state change.

    Maya file import itself is not undoable. The hidden cache deliberately remains
    after undo; active shape and texture changes belong to one undo chunk.
    """
    for shape in cmds.listRelatives(target, shapes=True, fullPath=True, type="mesh") or []:
        if cmds.objExists(shape + "." + TAG) and cmds.getAttr(shape + "." + TAG) == key:
            core._editable(shape)
            return shape
    if not cmds.pluginInfo("objExport", query=True, loaded=True):
        cmds.loadPlugin("objExport", quiet=True)
    imported = []
    new = None
    try:
        with core.root_namespace(), core.preserve_selection():
            imported = cmds.file(path, i=True, type="OBJ", namespace=":", returnNewNodes=True,
                                 executeScriptNodes=False)
            shapes = [n for n in imported if cmds.objExists(n) and cmds.nodeType(n) == "mesh"]
            if len(shapes) != 1:
                raise core.ToolError("VFace OBJ 必须只有一个头部网格。")
            parent, shape, mesh = core.mesh(shapes[0], editable=True)
            if counts and (mesh.numVertices, mesh.numPolygons) != counts:
                raise core.ToolError("头部拓扑数量与此预设不匹配，未替换原模型。")
            cmds.setAttr(shape + ".intermediateObject", True)
            new = cmds.parent(shape, target, shape=True, relative=True)[0]
            cmds.delete(parent)
            new = cmds.rename(new, label + "Shape")
            new = cmds.ls(new, long=True)[0]
            cmds.addAttr(new, longName=TAG, dataType="string")
            cmds.setAttr(new + "." + TAG, key, type="string")
            return new
    except Exception:
        # Only remove objects imported by this operation, never the original head.
        if new and cmds.objExists(new):
            cmds.delete(new)
        for node in imported:
            if cmds.objExists(node):
                cmds.delete(node)
        raise


def _extra_target(name):
    matches = set(cmds.ls(name, long=True, type="transform") or [])
    matches.update(cmds.ls(name + "_Mesh", long=True, type="transform") or [])
    if len(matches) != 1:
        raise core.ToolError("预设需要唯一配套模型：" + name)
    target, shape, _ = core.mesh(next(iter(matches)), editable=True)
    for plug, incoming in (("inMesh", True), ("outMesh", False), ("worldMesh", False)):
        if cmds.listConnections(shape + "." + plug, source=incoming, destination=not incoming):
            raise core.ToolError("配套模型有历史或下游依赖，未切换：" + name)
    if cmds.getAttr(shape + ".intermediateObject", lock=True):
        raise core.ToolError("配套模型形状已锁定：" + name)
    groups = set(cmds.listConnections(shape, type="shadingEngine") or [])
    if len(groups) != 1:
        raise core.ToolError("配套模型需要单一材质分配：" + name)
    attrs = {attr: cmds.getAttr(shape + "." + attr) for attr in
             ("aiSubdivType", "aiSubdivIterations", "aiDispHeight", "aiDispZeroValue", "aiOpaque")}
    return target, shape, next(iter(groups)), attrs


def _owned_node(name, node_type):
    if cmds.objExists(name):
        if cmds.nodeType(name) != node_type or not cmds.objExists(name + ".yuejunVFaceManaged"):
            raise core.ToolError("存在非工具创建的同名节点：" + name)
        core._editable(name)
        return name
    node = (cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=name)
            if node_type == "shadingEngine" else cmds.createNode(node_type, name=name))
    cmds.addAttr(node, longName="yuejunVFaceManaged", attributeType="bool", defaultValue=True)
    return node


def _sclera_material(side, paths, color, prepare=False):
    prefix = "VFace_Sclera_" + side
    fresh = not cmds.objExists(prefix + "_MAT")
    shader = _owned_node(prefix + "_MAT", "aiStandardSurface")
    group = _owned_node(prefix + "_SG", "shadingEngine")
    if not cmds.isConnected(shader + ".outColor", group + ".surfaceShader"):
        cmds.connectAttr(shader + ".outColor", group + ".surfaceShader")
    if fresh:
        for attr, value in (("base", 1), ("specular", 1), ("specularRoughness", 0.22), ("specularIOR", 1.38)):
            cmds.setAttr(shader + "." + attr, value)
    disp = _owned_node(prefix + "_DISP", "displacementShader")
    for kind, dest, output, space in (("albedo", shader + ".baseColor", "outColor", color),
                                      ("displacement", disp + ".displacement", "outColorR", "Raw")):
        texture = _owned_node(prefix + "_" + kind, "file")
        placement = _owned_node(prefix + "_" + kind + "_UV", "place2dTexture")
        for output_uv, input_uv in (("outUV", "uvCoord"), ("outUvFilterSize", "uvFilterSize")):
            if not cmds.isConnected(placement + "." + output_uv, texture + "." + input_uv):
                cmds.connectAttr(placement + "." + output_uv, texture + "." + input_uv)
        if not prepare:
            cmds.setAttr(texture + ".fileTextureName", paths[side + "_" + kind], type="string")
            cmds.setAttr(texture + ".ignoreColorSpaceFileRules", True)
            cmds.setAttr(texture + ".colorSpace", space, type="string")
        if not cmds.isConnected(texture + "." + output, dest):
            cmds.connectAttr(texture + "." + output, dest)
    if not cmds.isConnected(disp + ".displacement", group + ".displacementShader"):
        cmds.connectAttr(disp + ".displacement", group + ".displacementShader")
    return group


def _organize(targets, identity):
    root = _owned_node("VFace_GRP", "transform")
    if not cmds.objExists(root + ".vfaceIdentity"):
        cmds.addAttr(root, longName="vfaceIdentity", dataType="string")
    cmds.setAttr(root + ".vfaceIdentity", identity, type="string")
    for category in ("Head", "Eyes", "Eyelashes", "Eyebrows"):
        group = _owned_node("VFace_" + category + "_GRP", "transform")
        parent = cmds.listRelatives(group, parent=True) or []
        if parent != [root]:
            cmds.parent(group, root, absolute=True)
        for target, kind in targets:
            if kind == category and (cmds.listRelatives(target, parent=True) or []) != [group]:
                cmds.parent(target, group, absolute=True)


def apply(folder):
    source = assets(folder)
    extras = extra_assets(folder)
    target, old, vertices, faces = validate_scene()
    plans = [(name, group, _extra_target(name)) for _, name, group in EXTRAS]
    color = linear_space()
    if not cmds.undoInfo(query=True, state=True):
        raise core.ToolError("请先启用 Maya Undo。")
    project.ensure_project()
    session = project.SyncSession()
    identity = os.path.basename(os.path.normpath(folder))
    session.register_package(folder, "VFace/" + identity)
    local = session.copy_file(source["geometry"], "scene")
    paths = {key: session.resource(source[key]) for key in ("albedo", "displacement", "utility")}
    stat = os.stat(local)
    key = hashlib.sha256(json.dumps([os.path.realpath(local), stat.st_size, stat.st_mtime_ns]).encode("utf-8")).hexdigest()
    new = _stage_geometry(local, target, key, (vertices, faces), "VFace_" + identity + "_Head")
    staged = []
    for name, category, (transform, shape, material, attrs) in plans:
        path = session.copy_file(extras[name], "scene")
        stat = os.stat(path)
        signature = hashlib.sha256(json.dumps([os.path.realpath(path), stat.st_size, stat.st_mtime_ns]).encode("utf-8")).hexdigest()
        replacement = _stage_geometry(path, transform, signature, label="VFace_" + identity + "_" + name)
        staged.append((transform, shape, replacement, material, attrs, name, category))
    eye_paths = {key: session.resource(value) for key, value in extras.items() if not key.startswith("XYZ_")}
    # Arnold 2022 adds AOV aliases on shadingEngine creation; replaying that callback
    # inside a large undo chunk can abort redo. Stage unused material caches first.
    for side in ("left", "right"):
        _sclera_material(side, eye_paths, color, prepare=True)
    preview.mark(session)
    with core.undo_chunk("vface_switch"), core.preserve_selection():
        cmds.setAttr(old + ".intermediateObject", True)
        cmds.setAttr(new + ".intermediateObject", False)
        cmds.sets(new, edit=True, forceElement="aiStandardSurface1SG")
        for attr, value in (("aiSubdivType", 1), ("aiSubdivIterations", 4), ("aiDispHeight", 1),
                            ("aiDispZeroValue", 0), ("aiDispPadding", 1), ("aiDispAutobump", True)):
            cmds.setAttr(new + "." + attr, value)
        for node, texture, space in (("file4", "albedo", color), ("file2", "displacement", "Raw"),
                                     (UTILITY, "utility", "Raw")):
            cmds.setAttr(node + ".fileTextureName", paths[texture], type="string")
            cmds.setAttr(node + ".ignoreColorSpaceFileRules", True)
            cmds.setAttr(node + ".colorSpace", space, type="string")
        if not cmds.isConnected("file2.outColorR", "displacementShader1.displacement"):
            cmds.connectAttr("file2.outColorR", "displacementShader1.displacement", force=True)
        for transform, shape, replacement, material, attrs, name, category in staged:
            cmds.setAttr(shape + ".intermediateObject", True)
            cmds.setAttr(replacement + ".intermediateObject", False)
            if name.startswith("XYZ_sclera_"):
                side = "left" if "_left_" in name else "right"
                material = _sclera_material(side, eye_paths, color)
                attrs.update(aiSubdivType=1, aiSubdivIterations=2, aiDispHeight=1, aiDispZeroValue=0)
            for attr, value in attrs.items():
                cmds.setAttr(replacement + "." + attr, value)
            cmds.sets(replacement, edit=True, forceElement=material)
        _organize([(target, "Head")] + [(row[0], row[6]) for row in staged], identity)
    scene = cmds.file(query=True, sceneName=True)
    if scene and project.inside(scene, config.resource_root()) and not project.inside(scene, session.root):
        preview.install()
        preview.STATE.active = True  # Never allow saving back over a library preset.
    return "已切换 VFace {}：头部、眼睛、泪线、眉毛、睫毛及配套贴图。{}".format(identity, session.summary())
