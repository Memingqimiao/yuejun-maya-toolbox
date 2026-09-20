# -*- coding: utf-8 -*-
"""MetaHuman FBX import and reversible inspection materials; no UI."""
import math
import time
from collections import defaultdict
from itertools import product
import hashlib
import json
import os
from contextlib import contextmanager

from maya import cmds, mel
from maya.api import OpenMaya as om
from . import config, core, project, preview

TAG = "yuejunMetaHuman"
BACKUP = "yuejunMaterialBackup"
NETWORKS = "yuejunInspectionMaterials"
ROLE = "yuejunMetaHumanPart"
PARTS = {"head_lod0_mesh": "Head", "body_lod0_mesh": "Body",
         "eyeLeft_lod0_mesh": "Eyes", "eyeRight_lod0_mesh": "Eyes",
         "teeth_lod0_mesh": "Teeth"}
TEXTURES = {"Head": "Head_Base_Color.jpg", "Body": "Body_Base_Color.jpg",
            "Eyes": "eyes_color_map.jpg", "Teeth": "Teeth_DiffuseTexture.jpg"}


def _string(node, attr, value):
    if not cmds.attributeQuery(attr, node=node, exists=True):
        cmds.addAttr(node, longName=attr, dataType="string")
    cmds.setAttr(node + "." + attr, value, type="string")


def _uuid(node):
    return cmds.ls(node, uuid=True)[0]


def _resolve(uid):
    nodes = cmds.ls(uid, long=True) or []
    if len(nodes) != 1:
        raise core.ToolError("原模型或材质已删除，不能安全还原；请撤销相关删除操作。")
    return nodes[0]


def target():
    roots = set()
    selected = cmds.ls(selection=True, long=True, objectsOnly=True) or []
    for node in selected:
        while node:
            if cmds.attributeQuery(TAG, node=node, exists=True):
                roots.add(node)
                break
            parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
            node = parents[0] if parents else None
    if not selected:
        roots = set(cmds.ls("*." + TAG, objectsOnly=True, long=True) or [])
    if len(roots) != 1:
        raise core.ToolError("请选择一个由工具导入的 MetaHuman 组或其中的网格。")
    root = roots.pop()
    core._editable(root)
    return root


def import_model(sex):
    if sex not in ("Female", "Male"):
        raise core.ToolError("未知 MetaHuman 类型。")
    path = core.require_file("Models/Metahuman/Model/MH_Base_" + sex + ".fbx")
    if not cmds.pluginInfo("fbxmaya", query=True, loaded=True):
        cmds.loadPlugin("fbxmaya", quiet=True)
    project.ensure_project()
    session = project.SyncSession(path)
    local = session.copy_file(path, "scene")
    session.flush()
    old_mode = mel.eval("FBXImportMode -q;")
    try:
        mel.eval('FBXImportMode -v "add";')
        with core.undo_chunk("metahuman_import"), core.root_namespace():
            nodes = cmds.file(local, i=True, type="FBX", namespace=":",
                              mergeNamespacesOnClash=False, renameAll=True,
                              returnNewNodes=True, executeScriptNodes=False) or []
            transforms = set(cmds.ls(nodes, type="transform", long=True) or [])
            tops = [node for node in transforms if not
                    set(cmds.listRelatives(node, parent=True, fullPath=True) or []) & transforms]
            if not tops:
                raise core.ToolError("FBX 没有可导入的模型。")
            root = cmds.group(tops, name="MetaHuman_" + sex)
            _string(root, TAG, sex)
            _string(root, BACKUP, "")
            _string(root, NETWORKS, "{}")
            for shape in cmds.listRelatives(root, allDescendents=True, type="mesh", fullPath=True) or []:
                parent = cmds.listRelatives(shape, parent=True, fullPath=True)[0]
                name = parent.rsplit("|", 1)[-1].rsplit(":", 1)[-1]
                # Maya appends digits when importing a second copy into root namespace.
                for base, role in PARTS.items():
                    if name == base or (name.startswith(base) and name[len(base):].isdigit()):
                        _string(shape, ROLE, role)
                        break
            preview.mark(session)
            cmds.select(root, replace=True)
    finally:
        mel.eval('FBXImportMode -v "{}";'.format(old_mode))
    return "已导入 MetaHuman {}。点击“观察贴图 / 还原”查看贴图，再次点击还原材质。".format(sex)


def _meshes(root):
    shapes = [s for s in cmds.listRelatives(root, allDescendents=True, type="mesh", fullPath=True) or []
              if cmds.attributeQuery(ROLE, node=s, exists=True) and not cmds.getAttr(s + ".intermediateObject")]
    for shape in shapes:
        core._editable(shape)
    if not shapes:
        raise core.ToolError("没有可编辑的 MetaHuman 网格。")
    return shapes


def _snapshot(shape):
    selection = om.MSelectionList()
    selection.add(shape)
    dag = selection.getDagPath(0)
    fn = om.MFnMesh(dag)
    shaders, indices = fn.getConnectedShaders(dag.instanceNumber())
    if any(index < 0 for index in indices):
        raise core.ToolError("模型有未分配材质的面，请先分配材质。")
    groups = []
    for index, shader in enumerate(shaders):
        groups.append([_uuid(om.MFnDependencyNode(shader).name()),
                       [face for face, assigned in enumerate(indices) if assigned == index]])
    return {"mesh": _uuid(shape), "faces": fn.numPolygons, "groups": groups}


def _members(shape, faces):
    """Compact consecutive face runs to keep large assignments manageable."""
    if not faces:
        return []
    result = []
    first = last = faces[0]
    for face in faces[1:] + [None]:
        if face is not None and face == last + 1:
            last = face
            continue
        result.append("{}.f[{}:{}]".format(shape, first, last))
        first = last = face
    return result


def apply():
    root = target()
    shapes = _meshes(root)
    paths = {role: core.require_file("Models/Metahuman/Texture/" + name)
             for role, name in TEXTURES.items()}
    session = project.SyncSession()
    paths = {role: session.copy_file(path, "texture") for role, path in paths.items()}
    session.flush()
    with core.undo_chunk("metahuman_textures"), core.preserve_selection():
        if not cmds.getAttr(root + "." + BACKUP):
            _string(root, BACKUP, json.dumps([_snapshot(shape) for shape in shapes]))
        networks = json.loads(cmds.getAttr(root + "." + NETWORKS))
        for role, path in paths.items():
            cached = networks.get(role)
            if cached and all(cmds.ls(uid) for uid in cached):
                sg, file_node = [_resolve(uid) for uid in cached]
            else:
                material = cmds.shadingNode("lambert", asShader=True, name="MH_" + role + "_Preview")
                sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=material + "SG")
                file_node = cmds.shadingNode("file", asTexture=True, name="MH_" + role + "_Texture")
                place = cmds.shadingNode("place2dTexture", asUtility=True, name="MH_" + role + "_UV")
                for attr in ("coverage", "translateFrame", "rotateFrame", "mirrorU", "mirrorV", "stagger",
                             "wrapU", "wrapV", "repeatUV", "offset", "rotateUV", "noiseUV",
                             "vertexUvOne", "vertexUvTwo", "vertexUvThree", "vertexCameraOne"):
                    cmds.connectAttr(place + "." + attr, file_node + "." + attr)
                cmds.connectAttr(place + ".outUV", file_node + ".uvCoord")
                cmds.connectAttr(place + ".outUvFilterSize", file_node + ".uvFilterSize")
                cmds.connectAttr(file_node + ".outColor", material + ".color")
                cmds.connectAttr(material + ".outColor", sg + ".surfaceShader")
                networks[role] = [_uuid(sg), _uuid(file_node)]
            cmds.setAttr(file_node + ".fileTextureName", path.replace("\\", "/"), type="string")
            cmds.setAttr(file_node + ".colorSpace", "sRGB", type="string")
            for shape in shapes:
                if cmds.getAttr(shape + "." + ROLE) == role:
                    cmds.sets(shape, edit=True, forceElement=sg)
        _string(root, NETWORKS, json.dumps(networks))
        preview.mark(session)
    return "已应用头部、身体、眼睛、牙齿观察贴图；视口按 6 显示贴图。原材质已记录，可一键还原。"


def restore():
    root = target()
    data = cmds.getAttr(root + "." + BACKUP)
    if not data:
        return "当前没有需要还原的观察贴图。"
    assignments = []
    for record in json.loads(data):
        shape = _resolve(record["mesh"])
        if not shape.startswith(root + "|"):
            raise core.ToolError("材质备份属于其他模型；请使用工具重新导入独立副本。")
        core._editable(shape)
        if cmds.polyEvaluate(shape, face=True) != record["faces"]:
            raise core.ToolError("网格已锁定或面数量发生变化，无法安全还原原材质分配。")
        original_groups = [(uid, faces) for uid, faces in record["groups"] if faces]
        if not original_groups:
            raise core.ToolError("材质备份没有有效分配，未执行还原。")
        # Replace the whole-object preview membership before restoring face overrides.
        assignments.append((_resolve(original_groups[0][0]), [shape]))
        for uid, faces in original_groups:
            sg = _resolve(uid)
            core._editable(sg)
            members = _members(shape, faces)
            if members:
                assignments.append((sg, members))
    with core.undo_chunk("metahuman_restore"), core.preserve_selection():
        for sg, members in assignments:
            cmds.sets(members, edit=True, forceElement=sg)
        _string(root, BACKUP, "")
    return "已还原应用观察贴图前的材质分配；模型、UV 和绑定保持不变。"


UV_STATE = "yuejunMHUVState"
HEAD_TOPOLOGY = "6c3a0ee8e854787c5294e315dc0de785a4989862775b73facac128951859832a"


def topology_signature(fn):
    data = [list(values) for values in fn.getVertices()]
    data.append([list(fn.getEdgeVertices(index)) for index in range(fn.numEdges)])
    return hashlib.sha256(json.dumps(data, separators=(",", ":")).encode("ascii")).hexdigest()


def toggle_textures():
    root = target()
    return restore() if cmds.getAttr(root + "." + BACKUP) else apply()


@contextmanager
def without_soft_selection():
    enabled = cmds.softSelect(query=True, softSelectEnabled=True)
    try:
        if enabled:
            cmds.softSelect(softSelectEnabled=False)
        yield
    finally:
        if enabled:
            cmds.softSelect(softSelectEnabled=True)


def toggle_uv():
    selected = cmds.ls(selection=True, objectsOnly=True, long=True) or []
    if len(selected) != 1:
        raise core.ToolError("请选择一个 MetaHuman 头部网格；支持任意名称。")
    node, shape, fn = core.mesh(selected[0], editable=True)
    if topology_signature(fn) != HEAD_TOPOLOGY:
        raise core.ToolError("头部拓扑或面/边编号与配套 MetaHuman 不一致，未修改 UV。")
    data = cmds.getAttr(shape + "." + UV_STATE) if cmds.attributeQuery(UV_STATE, node=shape, exists=True) else ""
    sets = list(fn.getUVSetNames())
    if data:
        state = json.loads(data)
        if state["original"] not in sets or state["backup"] not in sets:
            raise core.ToolError("原 UV 集或备份已被删除，无法自动还原。")
        with core.undo_chunk("mh_restore_uv"), without_soft_selection(), core.preserve_selection():
            cmds.polyUVSet(shape, copy=True, uvSet=state["backup"], newUVSet=state["original"])
            cmds.polyUVSet(shape, currentUVSet=True, uvSet=state["original"])
            cmds.polyUVSet(shape, delete=True, uvSet=state["backup"])
            _string(shape, UV_STATE, "")
        return "已精确还原切换前的 UV（可撤销）。"
    if not sets:
        raise core.ToolError("所选模型没有 UV 集。")
    original = fn.currentUVSetName()
    backup = "Yuejun_MH_UV_Backup"
    while backup in sets:
        backup += "_1"
    path = core.require_file("Scripts/Skin_qieUV.mel")
    with open(path, encoding="utf-8-sig") as stream:
        plan = core.skin_plan(stream.read(), "cut_uv", node)
    with core.undo_chunk("mh_cut_uv"), without_soft_selection(), core.preserve_selection():
        cmds.polyUVSet(shape, copy=True, uvSet=original, newUVSet=backup)
        cmds.polyUVSet(shape, currentUVSet=True, uvSet=original)
        for command, args, kwargs in plan:
            getattr(cmds, command)(*args, **kwargs)
        _string(shape, UV_STATE, json.dumps({"original": original, "backup": backup}))
    return "MH 切 UV 完成；再次点击同一按钮恢复切换前的 UV（可撤销）。"



def boundary_vertices(fn):
    result = set()
    iterator = om.MItMeshEdge(fn.dagPath())
    while not iterator.isDone():
        if iterator.onBoundary():
            result.update((iterator.vertexId(0), iterator.vertexId(1)))
        iterator.next()
    return sorted(result)


def seam_pairs(points_a, ids_a, points_b, ids_b, tolerance):
    # Search adjacent cells too: rounding alone misses pairs across a cell edge.
    def cell(point):
        return tuple(int(math.floor(value / tolerance)) for value in (point.x, point.y, point.z))
    buckets = defaultdict(list)
    for index in ids_a:
        buckets[cell(points_a[index])].append(index)
    candidates = {}
    reverse = defaultdict(list)
    for j in ids_b:
        key = cell(points_b[j])
        matches = []
        for offset in product((-1, 0, 1), repeat=3):
            for i in buckets.get(tuple(key[k] + offset[k] for k in range(3)), ()):
                if points_a[i].distanceTo(points_b[j]) <= tolerance:
                    matches.append(i)
        if len(matches) == 1:
            candidates[j] = matches[0]
        for i in matches:
            reverse[i].append(j)
    return [(i, j) for j, i in candidates.items() if len(reverse[i]) == 1]


def fix_seams(tolerance=0.01):
    """Average only unambiguous coincident boundary normals, with native undo."""
    started = time.perf_counter()
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise core.ToolError("接缝距离容差必须大于零。")
    selected = cmds.ls(selection=True, objectsOnly=True, long=True) or []
    if len(selected) != 2:
        raise core.ToolError("请同时选择头部和身体两个网格，顺序不限。")
    meshes = [core.mesh(node, editable=True) for node in selected]
    if meshes[0][1] == meshes[1][1]:
        raise core.ToolError("请选择两个不同的网格。")
    fns = [entry[2] for entry in meshes]
    points = [fn.getPoints(om.MSpace.kWorld) for fn in fns]
    pairs = seam_pairs(points[0], boundary_vertices(fns[0]), points[1], boundary_vertices(fns[1]), tolerance)
    if not pairs:
        raise core.ToolError("未找到唯一对应的重合边界点，请检查头部与身体的对齐；未修改模型。")
    normals = [fn.getVertexNormals(False, om.MSpace.kWorld) for fn in fns]
    # polyNormalPerVertex writes object-space normals; world normals require
    # the inverse of the normal matrix, i.e. transpose(object-to-world).
    matrices = [fn.dagPath().inclusiveMatrix().transpose() for fn in fns]
    batches = defaultdict(list)
    count = 0
    for i, j in pairs:
        normal = om.MVector(normals[0][i]).normal() + om.MVector(normals[1][j]).normal()
        if normal.length() < 1e-8:
            continue
        normal.normalize()
        for side, index in enumerate((i, j)):
            local = normal * matrices[side]
            if local.length() < 1e-8:
                raise core.ToolError("模型变换不可逆，请检查零缩放；未修改模型。")
            local.normalize()
            key = tuple(round(value, 12) for value in (local.x, local.y, local.z))
            batches[key].append("{}.vtx[{}]".format(meshes[side][1], index))
        count += 1
    if not count:
        raise core.ToolError("匹配处法线方向相反，无法安全平均；请先检查面朝向。")
    with core.undo_chunk("fix_metahuman_seams"), without_soft_selection(), core.preserve_selection():
        for normal, vertices in batches.items():
            cmds.polyNormalPerVertex(vertices, xyz=normal)
    return "已修复 {} 对接缝顶点法线，耗时 {:.2f} 秒（可撤销）；不移动顶点。".format(count, time.perf_counter() - started)
