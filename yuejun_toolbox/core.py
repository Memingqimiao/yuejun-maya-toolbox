# -*- coding: utf-8 -*-
"""Scene operations. No windows, dialogs, string callbacks or deferred exec."""
import os
import re
import shutil
import uuid
from contextlib import contextmanager

from maya import cmds, mel
from maya.api import OpenMaya as om

from . import config, project, preview


class ToolError(RuntimeError):
    """An actionable error to be displayed by the UI boundary."""


@contextmanager
def undo_chunk(label):
    """Only roll back our own topmost chunk, never an older user action."""
    if not cmds.undoInfo(query=True, state=True):
        raise ToolError("Maya 撤销已关闭。请先启用 Undo，再执行场景修改。")
    token = "Yuejun_{}_{}".format(label, uuid.uuid4().hex)
    cmds.undoInfo(openChunk=True, chunkName=token)
    failed = False
    try:
        yield
    except BaseException:
        failed = True
        raise
    finally:
        cmds.undoInfo(closeChunk=True)
        if failed and not cmds.undoInfo(query=True, undoQueueEmpty=True):
            if cmds.undoInfo(query=True, undoName=True) == token:
                try:
                    cmds.undo()
                except Exception as error:
                    cmds.warning("自动撤销失败，请检查场景：{}".format(error))


@contextmanager
def preserve_selection():
    snapshot = om.MGlobal.getActiveSelectionList()
    try:
        yield
    finally:
        # MSelectionList follows renamed DAG nodes; our tools do not delete them.
        try:
            names = snapshot.getSelectionStrings()
            if names:
                cmds.select(names, replace=True)
            else:
                cmds.select(clear=True)
        except Exception as error:
            cmds.warning("无法完整恢复选择：{}".format(error))


def require_file(relative):
    path = config.asset_path(relative)
    if not os.path.isfile(path):
        raise ToolError("找不到资源文件：{}。请检查资源根目录。".format(path))
    return path


def _editable(node):
    if cmds.referenceQuery(node, isNodeReferenced=True):
        raise ToolError("不能修改引用节点：{}。请使用本地模型副本。".format(node))
    if any(cmds.lockNode(node, query=True, lock=True) or []):
        raise ToolError("节点已锁定：{}".format(node))


def mesh(node, editable=False):
    """Resolve one unambiguous, non-instanced mesh without changing selection."""
    matches = cmds.ls(node, long=True) or []
    if len(matches) != 1 or "." in matches[0]:
        raise ToolError("需要唯一的完整网格对象：{}".format(node))
    node = matches[0]
    if cmds.nodeType(node) == "transform":
        shapes = cmds.listRelatives(node, shapes=True, noIntermediate=True,
                                    fullPath=True, type="mesh") or []
        if len(shapes) != 1:
            raise ToolError("{} 必须包含且仅包含一个可见网格。".format(node))
        shape = shapes[0]
    elif cmds.nodeType(node) == "mesh":
        shape = node
        node = (cmds.listRelatives(shape, parent=True, fullPath=True) or [""])[0]
    else:
        raise ToolError("{} 不是多边形网格。".format(node))
    selection = om.MSelectionList()
    selection.add(shape)
    dag = selection.getDagPath(0)
    if dag.isInstanced():
        raise ToolError("暂不修改实例网格，请先使用独立副本：{}".format(node))
    if editable:
        _editable(node)
        _editable(shape)
    return node, shape, om.MFnMesh(dag)


def named_mesh(name, editable=False):
    # Include namespaced imports and refuse ambiguous choices instead of picking first.
    candidates = set(cmds.ls(name, long=True, type="transform") or [])
    candidates.update(cmds.ls("*:" + name, long=True, type="transform", recursive=True) or [])
    if len(candidates) != 1:
        raise ToolError("{}：需要恰好一个匹配模型，当前找到 {} 个。请整理同名模型。".format(name, len(candidates)))
    return mesh(next(iter(candidates)), editable=editable)


_BLEND_SOURCE = {"uuid": "", "name": ""}


def _short(node):
    return node.rsplit("|", 1)[-1]


def _topology(mesh_fn):
    return mesh_fn.numVertices, mesh_fn.numEdges, mesh_fn.numPolygons


def _selected_meshes():
    """Selected mesh transforms in pick order, without duplicates."""
    result = []
    for node in cmds.ls(selection=True, long=True, objectsOnly=True) or []:
        if node not in result and (
                cmds.nodeType(node) == "mesh" or
                cmds.listRelatives(node, shapes=True, noIntermediate=True, type="mesh")):
            result.append(node)
    return result


def mark_blend_source():
    """Remember the selected mesh as the BS source shape; the scene is not changed."""
    selected = _selected_meshes()
    if len(selected) != 1:
        raise ToolError("请只选中一个新形状模型，当前选中 {} 个网格。".format(len(selected)))
    node, _, mesh_fn = mesh(selected[0])
    # UUIDs survive renaming and reparenting, unlike the original fixed Mubiao name.
    _BLEND_SOURCE["uuid"] = (cmds.ls(node, uuid=True) or [""])[0]
    _BLEND_SOURCE["name"] = _short(node)
    return "已记住目标形状：{}（{} 点 / {} 面）。再选中要被修改的模型，点击 BS切换。".format(
        _short(node), mesh_fn.numVertices, mesh_fn.numPolygons)


def _marked_blend_source():
    if not _BLEND_SOURCE["uuid"]:
        raise ToolError("尚未标记目标形状。请先选中新形状模型点击“BS先点我”，或同时选中两个模型再点击本按钮。")
    matches = cmds.ls(_BLEND_SOURCE["uuid"], long=True) or []
    if len(matches) != 1:
        raise ToolError("标记的目标形状 {} 已不在场景中，请重新点击“BS先点我”。".format(
            _BLEND_SOURCE["name"] or "模型"))
    return matches[0]


def blend_target(delete_source=True):
    """Transfer a shape between any two meshes that share the same topology.

    The original MEL required MetaHuman naming: it blended a node called Mubiao
    onto a node called Skin. Both meshes now come from the selection instead.
    """
    selected = _selected_meshes()
    if len(selected) > 2:
        raise ToolError("最多选中两个模型（先新形状、后被修改模型），当前选中 {} 个。".format(len(selected)))
    if len(selected) == 2:
        source_node, base_node = selected
    elif len(selected) == 1:
        source_node, base_node = _marked_blend_source(), selected[0]
    else:
        raise ToolError("请选中要被修改的模型；或同时选中新形状和被修改模型。")

    source, _, source_fn = mesh(source_node, editable=delete_source)
    base, _, base_fn = mesh(base_node, editable=True)
    if source == base:
        raise ToolError("新形状和被修改模型不能是同一个：{}。".format(_short(base)))
    if _topology(source_fn) != _topology(base_fn):
        raise ToolError(
            "两个模型拓扑不一致，无法传递形状。{}：{} 点 / {} 边 / {} 面；{}：{} 点 / {} 边 / {} 面。"
            "请使用点、边、面数量完全相同的模型。".format(
                _short(source), *(_topology(source_fn) + (_short(base),) + _topology(base_fn))))

    # The original MEL ran delete -ch too; name the deformers it will take with it.
    existing = [node for node in set(cmds.listHistory(base, pruneDagObjects=True) or [])
                if cmds.nodeType(node) in ("skinCluster", "blendShape", "cluster", "lattice",
                                           "wrap", "deltaMush", "nonLinear", "ffd")]
    with undo_chunk("blend_target"):
        deformer = cmds.blendShape(source, base, weight=(0, 1.0))[0]
        cmds.setAttr(deformer + ".envelope", 1)
        cmds.delete(base, constructionHistory=True)
        if delete_source:
            cmds.delete(source)
        cmds.select(base, replace=True)
    if delete_source and _BLEND_SOURCE["uuid"] and not cmds.ls(_BLEND_SOURCE["uuid"]):
        _BLEND_SOURCE.update(uuid="", name="")
    return "已将 {} 的造型传给 {} 并清除历史{}（可撤销）。{}".format(
        _short(source), _short(base),
        "，已删除新形状模型" if delete_source else "，保留新形状模型",
        "注意：清除历史同时移除了 {} 上原有的 {}。".format(
            _short(base), "、".join(sorted({cmds.nodeType(node) for node in existing})))
        if existing else "")


def update_growth():
    """Transfer selected source positions through the original growth UV layout."""
    selected = cmds.ls(selection=True, objectsOnly=True, long=True) or []
    if len(selected) != 1:
        raise ToolError("请选择一个作为更新来源的头部网格，名称不限。")
    source, source_shape, source_fn = mesh(selected[0], editable=False)
    if "map1" not in source_fn.getUVSetNames():
        raise ToolError("来源模型缺少 map1 UV 集，无法按 UV 更新生长体。")
    targets = []
    for name in ("Hair_Grtuv", "Brow_Grtuv", "Lash_Grtuv", "Beard_Grtuv"):
        node, shape, fn = named_mesh(name, editable=True)
        if shape == source_shape:
            raise ToolError("请选择头部来源模型，不要选择生长体。")
        if not {"Skin", "Hair"}.issubset(set(fn.getUVSetNames())):
            raise ToolError("{} 缺少 Skin / Hair UV 集，请使用配套生长体。".format(name))
        deformers = cmds.ls(cmds.listHistory(node) or [], type="geometryFilter") or []
        if deformers:
            raise ToolError("{} 已有变形器，更新会烘焙历史；请使用未绑定的生长体副本。".format(name))
        targets.append((node, shape))
    from .metahuman import without_soft_selection
    with undo_chunk("update_growth"), without_soft_selection(), preserve_selection():
        for node, shape in targets:
            cmds.polyUVSet(shape, currentUVSet=True, uvSet="Skin")
            cmds.transferAttributes(source, node, transferPositions=1, transferNormals=0,
                                    transferUVs=0, transferColors=0, sampleSpace=3,
                                    sourceUvSpace="map1", targetUvSpace="Skin",
                                    searchMethod=3, flipUVs=0, colorBorders=1)
            cmds.delete(node, constructionHistory=True)
            cmds.polyUVSet(shape, currentUVSet=True, uvSet="Hair")
    return "已按所选模型更新 4 个生长体（可撤销）；来源模型名称和历史保持不变。"


def run_legacy_mel(relative):
    """Keep original commands; isolate duplicate selection declarations in growth MEL."""
    if os.path.basename(relative).lower() == "skin_chuangjianshengzhangti.mel":
        with open(require_file(relative), "r", encoding="utf-8-sig") as stream:
            script = stream.read()
        # Original recorded MEL declares this local eight times in one scope.
        # Give each recorded selection snapshot its own scope; keep every command.
        script = re.sub(
            r'string\s+\$selection\[\]\s*=\s*`ls\s+-sl`\s*;\s*select\s+-r\s+\$selection\s*;',
            lambda match: "{ " + match.group(0) + " }", script)
        mel.eval("{\n" + script + "\n}")
        return "生长体更新完成。"
    path = require_file(relative).replace("\\", "/").replace('"', '\\"')
    mel.eval('source "{}";'.format(path))
    return "初版脚本执行完成：{}".format(os.path.basename(path))


def import_growth_original(relative):
    path = require_file(relative)
    session = project.SyncSession(path)
    local_path = session.copy_file(path, "scene")
    nodes = cmds.file(local_path, i=True, force=True, returnNewNodes=True)
    preview.mark(session)
    return "已导入生长体。" + project.localize(session, nodes)


@contextmanager
def root_namespace():
    """Resolve absolute names consistently, then restore the user's namespace mode."""
    previous = cmds.namespaceInfo(currentNamespace=True, absoluteName=True)
    relative = cmds.namespace(query=True, relativeNames=True)
    cmds.namespace(relativeNames=False)
    cmds.namespace(setNamespace=":")
    try:
        yield
    finally:
        cmds.namespace(setNamespace=previous if cmds.namespace(exists=previous) else ":")
        cmds.namespace(relativeNames=relative)


def node_namespace(node):
    """Namespace of a DG name or a full DAG path, always absolute."""
    return ":" + node.rsplit("|", 1)[-1].rpartition(":")[0].lstrip(":")


def namespace_nodes(roots, nodes=None):
    # Maya 2022 rejects certain namespaceInfo dagPath/absoluteName combinations.
    # ls(long=True) gives unambiguous DAG paths without combining those flags.
    if nodes is None:
        nodes = cmds.ls(long=True) or []
    return [node for node in nodes if any(
        node_namespace(node) == root or node_namespace(node).startswith(root + ":")
        for root in roots)]


def flatten_namespaces(roots):
    """Move only these namespace trees to root without Maya's collision renaming.

    Caller must own an undo chunk. All conflicts are checked before any move.
    Repeated short names are refused even across DAG parents to keep names unique.
    """
    namespaces = set(roots)
    all_nodes = cmds.ls(long=True) or []
    nodes = set(namespace_nodes(roots, all_nodes))
    for namespace in roots:
        namespaces.update(cmds.namespaceInfo(namespace, listOnlyNamespaces=True,
                                            recurse=True, absoluteName=True) or [])
    existing = [node for node in all_nodes if node_namespace(node) == ":"]
    occupied = {name.rsplit("|", 1)[-1].lstrip(":") for name in existing}
    desired = set()
    conflicts = set()
    for node in sorted(nodes):
        bare = node.rsplit("|", 1)[-1].rsplit(":", 1)[-1]
        if bare in occupied or bare in desired:
            conflicts.add(bare)
        desired.add(bare)
        _editable(node)
    if conflicts:
        raise ToolError("以下名称已存在或去掉前缀后重名：{}。请先处理重名再重试；未添加后缀。".format(
            "、".join(sorted(conflicts)[:12])))
    for namespace in sorted(namespaces, key=lambda name: (name.count(":"), name), reverse=True):
        # Do not use mergeNamespaceWithRoot or force=True: those can add suffixes.
        cmds.namespace(moveNamespace=(namespace, ":"), force=False)
        cmds.namespace(removeNamespace=namespace)
    return len(nodes)


def require_renderer(path):
    renderer = {"Test_Vray": "vrayformaya", "Test_Arnold": "mtoa",
                "Base_Arnold": "mtoa", "flippedNormals_eyeKit_Arnold": "mtoa",
                "Arnold_eye": "mtoa", "VRay_eye": "vrayformaya",
                "Disp_rs": "redshift4maya"}.get(os.path.splitext(os.path.basename(path))[0])
    if renderer:
        try:
            loaded = cmds.pluginInfo(renderer, query=True, loaded=True)
        except RuntimeError:
            loaded = False
        if not loaded:
            raise ToolError("请先在 Plug-in Manager 加载 {}。".format(renderer))


def scene_modified():
    return bool(cmds.file(query=True, modified=True))


def save_scene(path=None):
    if path:
        extension = os.path.splitext(path)[1].lower()
        if extension not in (".ma", ".mb"):
            raise ToolError("请使用 .ma 或 .mb 文件名保存场景。")
        previous_name = cmds.file(query=True, sceneName=True)
        cmds.file(rename=path)
        try:
            cmds.file(save=True, type="mayaBinary" if extension == ".mb" else "mayaAscii")
        except Exception:
            cmds.file(rename=previous_name or "untitled")
            raise
    else:
        if not cmds.file(query=True, sceneName=True):
            raise ToolError("未命名场景需要先选择保存路径。")
        cmds.file(save=True)
    if scene_modified():
        raise ToolError("场景未成功保存，已取消打开预设。")


def open_scene_preset(relative, discard_changes=False):
    """Original preset behavior: open the file, never import it into a namespace.

    Scene opening is not undoable. UI obtains save/discard/cancel before this call;
    direct callers cannot discard modified work unless they explicitly opt in.
    """
    path = require_file(relative)
    require_renderer(path)
    if scene_modified() and not discard_changes:
        raise ToolError("当前场景尚未保存，请先保存后再打开预设。")
    project.ensure_project()
    session = project.SyncSession(path)
    session.bundle()
    local_path = session.copy_file(path, "scene")
    cmds.file(local_path, open=True, force=bool(discard_changes), executeScriptNodes=False)
    preview.mark(session)
    result = project.localize(session)
    # Maya opening a scene does not establish its workspace; keep the chosen project.
    # Remapped attributes stay dirty for the artist's normal Save workflow.
    return "已加载预设：{}。{} {}".format(os.path.basename(path), result,
        "设置项目后才能保存。" if session.preview else "请保存场景以保留路径更新。")


def import_asset(relative):
    """Original model/node import, explicitly rooted, with no temporary namespace."""
    path = require_file(relative)
    require_renderer(path)
    session = project.SyncSession(path)
    session.bundle()
    local_path = session.copy_file(path, "scene")
    with root_namespace(), preserve_selection():
        nodes = cmds.file(local_path, i=True, namespace=":", mergeNamespacesOnClash=True,
                          returnNewNodes=True, executeScriptNodes=False,
                          preserveReferences=True)
        preview.mark(session)
        report = project.localize(session, nodes)
    return "已直接导入 {} 个节点。{}".format(len(nodes or []), report)


_COMPONENT = re.compile(r"Skin\.(e|f)\[(\d+)(?::(\d+))?\]")
_MEL_COMMANDS = {"cut_uv": {"polyMapCut", "select", "polyEditUV"},
                 "restore_uv": {"select", "polyEditUV", "polyMergeUV"},
                 "zb_groups": {"select", "sets"}}


def skin_plan(text, key, node):
    """Parse only the original scripts' data format into cmds calls, without eval."""
    def objects(tokens):
        if not tokens:
            raise ToolError("资源脚本缺少对象参数。")
        result = []
        for token in tokens:
            if token != "Skin" and not _COMPONENT.fullmatch(token):
                raise ToolError("资源脚本包含不支持的对象：{}".format(token))
            result.append(node + token[len("Skin"):])
        return result

    plan = []
    for raw in text.split(";"):
        statement = raw.strip()
        if not statement:
            continue
        if key == "zb_groups" and re.fullmatch(
                r'\$createSetResult\s*=\s*`sets\s+-name\s+"Skin_set"`', statement):
            plan.append(("sets", [], {"name": "Skin_set"}))
            continue
        tokens = statement.split()
        command = tokens[0]
        if command not in _MEL_COMMANDS[key]:
            raise ToolError("资源脚本包含未支持的命令：{}".format(command))
        if command == "select" and len(tokens) >= 3 and tokens[1] in ("-r", "-tgl"):
            plan.append((command, objects(tokens[2:]),
                         {"replace" if tokens[1] == "-r" else "toggle": True}))
        elif command == "polyMapCut" and tokens[1:3] == ["-ch", "1"]:
            plan.append((command, objects(tokens[3:]), {"constructionHistory": True}))
        elif command == "polyEditUV" and len(tokens) == 5 and tokens[1] == "-u" and tokens[3] == "-v":
            if tokens[2] != "0" or tokens[4] not in ("1", "-1"):
                raise ToolError("UV 脚本偏移参数与原始格式不符。")
            plan.append((command, [], {"uValue": 0, "vValue": int(tokens[4])}))
        elif command == "polyMergeUV" and tokens[1:] == ["-d", "0.01", "-ch", "1", "Skin"]:
            plan.append((command, [node], {"distance": 0.01, "constructionHistory": True}))
        else:
            raise ToolError("资源脚本参数格式不支持：{}。未执行任何修改。".format(command))
    return plan


def run_skin_script(tool):
    """Use the supplied component data, never source arbitrary script statements."""
    path = require_file(tool.path)
    with open(path, "r", encoding="utf-8-sig") as stream:
        text = stream.read()
    node, _, mesh_fn = named_mesh("Skin", editable=True)
    components = list(_COMPONENT.finditer(text))
    if not components:
        raise ToolError("脚本未包含预期的 Skin 面/边数据。")
    for match in components:
        maximum = mesh_fn.numEdges if match.group(1) == "e" else mesh_fn.numPolygons
        start = int(match.group(2))
        end = int(match.group(3) or start)
        if start > end or end >= maximum:
            raise ToolError("模型拓扑不适用：{} 超出当前 Skin 的范围；尚未执行任何修改。".format(match.group(0)))
    if tool.key != "zb_groups" and not mesh_fn.getUVSetNames():
        raise ToolError("Skin 没有 UV 集。")
    plan = skin_plan(text, tool.key, node)
    with undo_chunk(tool.key), preserve_selection():
        for command, args, kwargs in plan:
            getattr(cmds, command)(*args, **kwargs)
    return "{}完成（可撤销）。".format(tool.label)


def configure_vray_skin():
    _, shape, _ = named_mesh("Skin", editable=True)
    if not mel.eval('exists "vray"'):
        raise ToolError("未找到 V-Ray 命令，请先安装并加载 Maya 2022 对应的 V-Ray。")
    with undo_chunk("vray_skin"):
        for group in ("vray_subdivision", "vray_subquality", "vray_displacement"):
            mel.eval('vray addAttributesFromGroup "{}" {} 1;'.format(shape, group))
        for attribute, value in (("vrayEdgeLength", 0.001),
                                 ("vrayMaxSubdivs", 5),
                                 ("vrayDisplacementShift", -0.5)):
            plug = shape + "." + attribute
            if not cmds.objExists(plug) or not cmds.getAttr(plug, settable=True):
                raise ToolError("V-Ray 属性不可写：{}".format(plug))
            cmds.setAttr(plug, value)
    return "Skin 的 V-Ray 属性设置完成（可撤销）。"


def run_gn(procedure):
    if procedure not in ("GN_Import", "GN_Export"):
        raise ToolError("未知 GN 命令。")
    if not mel.eval('exists "{}"'.format(procedure)):
        raise ToolError("找不到 {}。请先点击“检查 GN 安装”确认状态，或点击“安装 GN 插件”。".format(procedure))
    # GN owns its file dialogs, scene edits and undo behavior.
    session = project.SyncSession() if procedure == "GN_Import" else None
    before = set(cmds.ls(long=True) or []) if session else set()
    mel.eval(procedure + ";")
    if session:
        preview.mark(session)
        after = set(cmds.ls(long=True) or [])
        return "已执行 GN 导入。" + project.localize(session, list(after - before))
    return "已执行 {}。".format(procedure)


def _inside(path, root):
    try:
        return os.path.normcase(os.path.commonpath((root, path))) == os.path.normcase(root)
    except ValueError:
        # Windows resources and projects can be on different drives.
        return False


def copy_folder(source, destination):
    """Recursively copy missing files only, with exclusive creation to prevent clobbering."""
    if not os.path.isdir(source):
        raise ToolError("贴图源文件夹不存在：{}".format(source))
    source = os.path.realpath(source)
    destination = os.path.realpath(destination)
    if _inside(source, destination) or _inside(destination, source):
        raise ToolError("贴图来源和目标目录不能相同或互相包含。")
    copied = skipped = 0
    def walk_error(error):
        raise error

    for current, dirs, files in os.walk(source, followlinks=False, onerror=walk_error):
        dirs[:] = [name for name in dirs if not os.path.islink(os.path.join(current, name))]
        relative = os.path.relpath(current, source)
        target_dir = os.path.join(destination, relative)
        resolved_dir = os.path.realpath(target_dir)
        if not _inside(resolved_dir, destination):
            raise ToolError("目标子目录链接超出了贴图目录：{}".format(target_dir))
        for name in files:
            src = os.path.join(current, name)
            if os.path.islink(src):
                skipped += 1
                continue
            os.makedirs(target_dir, exist_ok=True)
            dst = os.path.join(target_dir, name)
            try:
                output = open(dst, "xb")
            except FileExistsError:
                skipped += 1
                continue
            try:
                with output, open(src, "rb") as stream:
                    shutil.copyfileobj(stream, output)
            except BaseException:
                # Only the incomplete file created by this call is removed.
                os.remove(dst)
                raise
            copied += 1
    return copied, skipped


def availability(tool):
    if tool.kind in ("mel", "import", "open", "legacy_import", "legacy_mel", "mh_import"):
        path = config.asset_path(tool.path)
        if not os.path.isfile(path):
            return False, "缺少文件：" + path
    return True, tool.help


def restore_xgen_guides():
    nodes = cmds.ls(type="xgmMakeGuide") or []
    if not nodes:
        return "未找到 xgmMakeGuide 节点。"
    connected = unchanged = skipped = 0
    with undo_chunk("restore_xgen_guides"):
        for node in nodes:
            try:
                _editable(node)
                # Only downstream destinations, never the upstream input mesh.
                downstream = set(cmds.listConnections(node, source=False, destination=True) or [])
                for output, input_attr in (("outputMesh", "inputMesh"), ("toGuide", "toMakeGuide")):
                    src = node + "." + output
                    targets = [other + "." + input_attr for other in downstream
                               if cmds.objExists(other + "." + input_attr)]
                    if not cmds.objExists(src) or not targets:
                        skipped += 1
                        continue
                    if len(targets) != 1:
                        cmds.warning("{} 下游目标不唯一，跳过 {}。".format(node, output))
                        skipped += 1
                        continue
                    dst = targets[0]
                    try:
                        _editable(dst.rsplit(".", 1)[0])
                        if cmds.getAttr(dst, lock=True):
                            raise ToolError("目标属性已锁定：" + dst)
                        if cmds.isConnected(src, dst):
                            unchanged += 1
                        else:
                            cmds.connectAttr(src, dst, force=True)
                            connected += 1
                    except Exception as error:
                        skipped += 1
                        cmds.warning("连接失败 {} → {}：{}".format(src, dst, error))
            except Exception as error:
                skipped += 1
                cmds.warning("跳过 {}：{}".format(node, error))
    return "XGen：修复 {} 处，已连接 {} 处，跳过 {} 处。".format(connected, unchanged, skipped)


def clean_unknown_nodes():
    nodes = set()
    for kind in ("unknown", "unknownDag", "unknownTransform"):
        nodes.update(cmds.ls(type=kind, long=True) or [])
    deleted = skipped = removed = 0
    with undo_chunk("clean_unknown_nodes"):
        for node in sorted(nodes, key=lambda name: name.count("|"), reverse=True):
            if not cmds.objExists(node):
                continue
            try:
                _editable(node)
                # Do not cascade-delete healthy children of an unknown DAG node.
                if cmds.listRelatives(node, children=True, fullPath=True):
                    raise ToolError("包含子节点，保留以避免连带删除")
                cmds.delete(node)
                deleted += 1
            except Exception as error:
                skipped += 1
                cmds.warning("保留 {}：{}".format(node, error))
    for plugin in cmds.unknownPlugin(query=True, list=True) or []:
        try:
            cmds.unknownPlugin(plugin, remove=True)
            removed += 1
        except Exception as error:
            skipped += 1
            cmds.warning("保留插件依赖 {}：{}".format(plugin, error))
    return "已删除 {} 个未知节点，移除 {} 个插件依赖，跳过 {} 项。插件依赖移除不可撤销。".format(deleted, removed, skipped)


def execute(key, **options):
    tool = config.TOOLS.get(key)
    if tool is None:
        raise ToolError("未知工具：{}".format(key))
    if tool.kind == "mh_fit":
        from . import mh_fit
        return (mh_fit.repair_indices if key == "mh_reindex" else mh_fit.generate)(**options)
    if tool.kind in ("mh_import", "mh"):
        from . import metahuman
        if tool.kind == "mh_import":
            return metahuman.import_model("Female" if key == "mh_female" else "Male")
        if key == "mh_seams":
            return metahuman.fix_seams()
        return metahuman.toggle_textures() if key == "mh_apply" else metahuman.toggle_uv()
    if key == "import_eye_arnold":
        from . import eyes
        return eyes.import_eye()
    if tool.kind == "legacy_import":
        return import_growth_original(tool.path)
    if tool.kind == "legacy_mel":
        return run_legacy_mel(tool.path)
    if tool.kind == "open":
        return open_scene_preset(tool.path)
    if tool.kind == "import":
        return import_asset(tool.path)
    if tool.kind == "mel":
        return run_skin_script(tool)
    if tool.kind == "gn":
        return run_gn(tool.path)
    if tool.kind == "gn_manage":
        from . import gn
        return gn.status() if key == "gn_check" else gn.install()
    actions = {"update_growth": update_growth, "rename_target": mark_blend_source, "blend_target": blend_target,
               "vray_skin": configure_vray_skin,
               "restore_xgen_guides": restore_xgen_guides,
               "clean_unknown_nodes": clean_unknown_nodes}
    return actions[key](**options)
