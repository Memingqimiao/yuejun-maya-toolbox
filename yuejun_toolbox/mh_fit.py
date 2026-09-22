# -*- coding: utf-8 -*-
"""UV-verified index recovery and reference accessory fitting. No UI."""
import json
import math
import os
import tempfile
from collections import Counter

from maya import cmds
from maya.api import OpenMaya as om
from . import core, metahuman as mh

KIT = "yuejunFitReference"
SOURCE = "yuejunFitSource"
OUTPUT = "yuejunFitOutputs"
COMMAND = "yuejunFitPointsV1"
PARTS = ("cartilage", "eyeEdge", "eyeLeft", "eyeRight", "eyelashes", "eyeshell", "saliva", "teeth")

# API point writes must be a genuine undoable command, not just an undo chunk.
PLUGIN = """import json
import maya.api.OpenMaya as om
def maya_useNewAPI():
    pass
class EditPoints(om.MPxCommand):
    def doIt(self, args):
        self.edits = []
        for name, points in json.loads(args.asString(0)):
            selection = om.MSelectionList(); selection.add(name)
            dag = selection.getDagPath(0)
            fn = om.MFnMesh(dag)
            inverse = dag.inclusiveMatrixInverse()
            new = om.MPointArray([om.MPoint(*p) * inverse for p in points])
            if len(new) != fn.numVertices:
                raise RuntimeError("Vertex count changed")
            self.edits.append((om.MObjectHandle(dag.node()), fn.getPoints(), new))
        self.redoIt()
    def redoIt(self):
        for handle, old, new in self.edits:
            om.MFnMesh(handle.object()).setPoints(new)
    def undoIt(self):
        for handle, old, new in reversed(self.edits):
            om.MFnMesh(handle.object()).setPoints(old)
    def isUndoable(self):
        return True
def initializePlugin(obj):
    om.MFnPlugin(obj, "Yuejun", "1.0", "Any").registerCommand("yuejunFitPointsV1", EditPoints)
def uninitializePlugin(obj):
    om.MFnPlugin(obj).deregisterCommand("yuejunFitPointsV1")
"""


def ensure_command():
    if hasattr(cmds, COMMAND):
        return
    folder = os.path.join(tempfile.gettempdir(), "YuejunToolbox", "plugins")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "yuejun_fit_points_v1.py")
    with open(path, "w", encoding="utf-8") as stream:
        stream.write(PLUGIN)
    cmds.loadPlugin(path, quiet=True)


def write_points(edits):
    getattr(cmds, COMMAND)(json.dumps([(shape, [[p.x, p.y, p.z] for p in points])
                                     for shape, points in edits]))


def selected_head():
    selected = cmds.ls(selection=True, objectsOnly=True, long=True) or []
    if len(selected) != 1:
        raise core.ToolError("请选择一个修改后的头部网格。")
    node, shape, fn = core.mesh(selected[0])
    if fn.numVertices != 24049 or fn.numPolygons != 24002:
        raise core.ToolError("头部数量与配套 MetaHuman 不符，无法可靠匹配。")
    return node, shape, fn


def reference(sex):
    if sex not in ("Female", "Male"):
        raise core.ToolError("请选择男或女参考模型。")
    roots = [n for n in cmds.ls("*." + KIT, objectsOnly=True, long=True) or []
             if cmds.getAttr(n + "." + KIT) == sex]
    if len(roots) > 1:
        raise core.ToolError("存在多套同类型参考缓存，请先整理隐藏的参考组。")
    if roots:
        root = roots[0]
    else:
        with core.preserve_selection():
            mh.import_model(sex)
            root = (cmds.ls(selection=True, long=True) or [])[0]
            root = cmds.rename(root, "Yuejun_MH_Reference_" + sex)
            cmds.deleteAttr(root + "." + mh.TAG)
            mh._string(root, KIT, sex)
            cmds.setAttr(root + ".visibility", False)
    found = {}
    for shape in cmds.listRelatives(root, allDescendents=True, type="mesh", fullPath=True) or []:
        name = shape.rsplit("|", 2)[-2].rsplit(":", 1)[-1]
        for part in ("head",) + PARTS:
            stem = part + "_lod0_mesh"
            if name == stem or (name.startswith(stem) and name[len(stem):].isdigit()):
                found[part] = shape
    if len(found) != len(PARTS) + 1:
        raise core.ToolError("参考素材缺少头部或配件，请检查隐藏参考组及男女 FBX。")
    return found


def uv_keys(fn):
    if "map1" not in fn.getUVSetNames():
        raise core.ToolError("缺少原始 map1 UV，不能修复编号。")
    u, v = fn.getUVs("map1")
    counts, vertices = fn.getVertices()
    uv_counts, ids = fn.getAssignedUVs("map1")
    if list(counts) != list(uv_counts):
        raise core.ToolError("部分面缺少 UV，不能修复编号。")
    keys = [set() for _ in range(fn.numVertices)]
    for vertex, uv in zip(vertices, ids):
        keys[vertex].add((round(u[uv], 6), round(v[uv], 6)))
    return [tuple(sorted(key)) for key in keys]


def faces(fn, remap=None):
    counts, vertices = fn.getVertices()
    result = []
    offset = 0
    for count in counts:
        face = list(vertices[offset:offset + count]); offset += count
        if remap is not None:
            face = [remap[v] for v in face]
        first = face.index(min(face))
        result.append(tuple(face[first:] + face[:first]))
    return Counter(result)


def correspondence(ref, target):
    if ref.numVertices != target.numVertices or ref.numPolygons != target.numPolygons:
        raise core.ToolError("头部拓扑数量不一致。")
    a, b = uv_keys(ref), uv_keys(target)
    if len(set(a)) != len(a) or len(set(b)) != len(b) or set(a) != set(b):
        raise core.ToolError("原 UV 已改变或存在歧义，未修改模型；请提供未改动的 MetaHuman UV。")
    lookup = {key: i for i, key in enumerate(b)}
    mapping = [lookup[key] for key in a]
    inverse = {target_id: ref_id for ref_id, target_id in enumerate(mapping)}
    if faces(ref) != faces(target, inverse):
        raise core.ToolError("UV 对应后的面连接或面朝向不一致，未修复编号。")
    return mapping


def repair_indices(sex="Female"):
    node, shape, fn = selected_head()
    refs = reference(sex)
    ref_fn = core.mesh(refs["head"])[2]
    mapping = correspondence(ref_fn, fn)
    if mh.topology_signature(fn) == mh.topology_signature(ref_fn):
        return "顶点、面和边编号已经符合参考模型，无需修复。"
    ensure_command()
    points = fn.getPoints(om.MSpace.kWorld)
    with core.undo_chunk("mh_repair_indices"):
        duplicate = cmds.duplicate(cmds.listRelatives(refs["head"], parent=True, fullPath=True)[0],
                                   returnRootsOnly=True, name="MH_Head_Reindexed")[0]
        duplicate = cmds.parent(duplicate, world=True)[0]
        cmds.setAttr(duplicate + ".visibility", True)
        cmds.delete(duplicate, constructionHistory=True)
        output_shape = core.mesh(duplicate)[1]
        write_points([(output_shape, [points[index] for index in mapping])])
        mh._string(output_shape, mh.ROLE, "Head")
        cmds.select(duplicate, replace=True)
    return "已生成编号正确的 MH_Head_Reindexed，保留原头部；新副本使用参考 UV/材质，不复制原绑定。"


def frame(a, b, c):
    x = b - a
    normal = x ^ (c - a)
    if x.length() < 1e-10 or normal.length() < 1e-10:
        raise core.ToolError("头部存在退化三角面，无法稳定适配配件。")
    area = normal.length()
    return x.normal(), normal.normal() ^ x.normal(), normal.normal(), area


def fit_points(ref_fn, deformed, points):
    original = ref_fn.getPoints(om.MSpace.kWorld)
    intersector = om.MMeshIntersector()
    intersector.create(ref_fn.object(), ref_fn.dagPath().inclusiveMatrix())
    result = []
    for point in points:
        hit = intersector.getClosestPoint(point)
        ids = ref_fn.getPolygonTriangleVertices(hit.face, hit.triangle)
        a, b, c = [original[i] for i in ids]
        aa, bb, cc = [deformed[i] for i in ids]
        u, v = hit.barycentricCoords
        base = a + (b - a) * v + (c - a) * (1 - u - v)
        moved = aa + (bb - aa) * v + (cc - aa) * (1 - u - v)
        x, y, n, area = frame(a, b, c)
        xx, yy, nn, new_area = frame(aa, bb, cc)
        offset = point - base
        scale = math.sqrt(new_area / area)
        result.append(moved + (xx * (offset * x) + yy * (offset * y) + nn * (offset * n)) * scale)
    return result


def preserve_shape(original, fitted):
    # Uniform scale + translation keeps eyeballs round and teeth from shearing.
    count = len(original)
    center = om.MVector(); moved = om.MVector()
    for a, b in zip(original, fitted):
        center += om.MVector(a); moved += om.MVector(b)
    center /= count; moved /= count
    a = [om.MVector(p) - center for p in original]
    b = [om.MVector(p) - moved for p in fitted]
    # Horn's quaternion fit: uniform scale and rigid rotation, without NumPy.
    cov = [[sum(x[i] * y[j] for x, y in zip(a, b)) for j in range(3)] for i in range(3)]
    xx, xy, xz = cov[0]; yx, yy, yz = cov[1]; zx, zy, zz = cov[2]
    matrix = [[xx+yy+zz, yz-zy, zx-xz, xy-yx],
              [yz-zy, xx-yy-zz, xy+yx, zx+xz],
              [zx-xz, xy+yx, -xx+yy-zz, yz+zy],
              [xy-yx, zx+xz, yz+zy, -xx-yy+zz]]
    shift = max(sum(abs(v) for v in row) for row in matrix) + 1e-12
    solutions = []
    for axis in range(4):
        q = [float(i == axis) for i in range(4)]
        for _ in range(100):
            value = [sum(matrix[i][j] * q[j] for j in range(4)) + shift*q[i] for i in range(4)]
            length = math.sqrt(sum(v*v for v in value))
            if length < 1e-12:
                break
            q = [v / length for v in value]
        score = sum(q[i] * matrix[i][j] * q[j] for i in range(4) for j in range(4))
        solutions.append((score, q))
    q = max(solutions, key=lambda item: item[0])[1]
    rotation = om.MQuaternion(q[1], q[2], q[3], q[0])
    rotated = [p.rotateBy(rotation) for p in a]
    before = sum(p*p for p in a)
    scale = sum(x*y for x,y in zip(rotated,b)) / before if before else 1.0
    if scale <= 0:
        raise core.ToolError("眼球或牙齿无法稳定适配，请检查头部是否翻转或塌陷。")
    return [om.MPoint(moved + p * scale) for p in rotated]



def generate(sex="Female"):
    node, shape, fn = selected_head()
    refs = reference(sex)
    ref_fn = core.mesh(refs["head"])[2]
    mapping = correspondence(ref_fn, fn)
    points = fn.getPoints(om.MSpace.kWorld)
    deformed = [points[i] for i in mapping]
    # Compute everything before editing existing generated accessories.
    fitted = {}
    for part in PARTS:
        original = core.mesh(refs[part])[2].getPoints(om.MSpace.kWorld)
        fitted[part] = fit_points(ref_fn, deformed, original)
        if part in ("eyeLeft", "eyeRight", "teeth"):
            fitted[part] = preserve_shape(original, fitted[part])
    roots = [n for n in cmds.ls("*." + SOURCE, objectsOnly=True, long=True) or []
             if (cmds.listConnections(n + "." + SOURCE, source=True, destination=False, shapes=True) or [])
             and mh._uuid((cmds.listConnections(n + "." + SOURCE, source=True, destination=False, shapes=True) or [])[0]) == mh._uuid(shape)]
    if len(roots) > 1:
        raise core.ToolError("该头部关联了多组配件，请先整理后再更新。")
    outputs = {}
    if roots:
        root = roots[0]
        core._editable(root)
        for part, uid in json.loads(cmds.getAttr(root + "." + OUTPUT)).items():
            target_shape = mh._resolve(uid)
            if not target_shape.startswith(root + "|"):
                raise core.ToolError("配件已移出原组，未执行更新。")
            _, _, target_fn = core.mesh(target_shape, editable=True)
            if target_fn.numVertices != len(fitted[part]):
                raise core.ToolError("配件拓扑已修改，不能覆盖更新。")
            if cmds.ls(cmds.listHistory(target_shape) or [], type="geometryFilter"):
                raise core.ToolError("配件已有绑定/变形器，未覆盖；请使用未绑定的副本。")
            outputs[part] = target_shape
        if set(outputs) != set(PARTS):
            raise core.ToolError("配件组不完整，请整理后重新生成。")
    ensure_command()
    with core.undo_chunk("mh_fit_accessories"):
        if not roots:
            root = cmds.group(empty=True, name="MH_Accessories")
            cmds.addAttr(root, longName=SOURCE, attributeType="message")
            cmds.connectAttr(shape + ".message", root + "." + SOURCE)
            for part in PARTS:
                parent = cmds.listRelatives(refs[part], parent=True, fullPath=True)[0]
                duplicate = cmds.duplicate(parent, returnRootsOnly=True, name="MH_" + part)[0]
                duplicate = cmds.parent(duplicate, root)[0]
                cmds.setAttr(duplicate + ".visibility", True)
                cmds.delete(duplicate, constructionHistory=True)
                outputs[part] = core.mesh(duplicate)[1]
            mh._string(root, OUTPUT, json.dumps({p: mh._uuid(s) for p, s in outputs.items()}))
        write_points([(outputs[part], fitted[part]) for part in PARTS])
        cmds.select(node, replace=True)
    return "已自动适配 8 个配件网格；眼球和牙齿保持整体形状。请检查眼睑贴合及口腔位置，必要时微调。"
