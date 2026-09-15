# -*- coding: utf-8 -*-
# Yuejun Toolbox 3.7.2 - Paste all into Maya's Python tab.
import sys as _yj_sys
import types as _yj_types
_yj_sources = {}

_yj_sources['config'] = r'''
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

'''

_yj_sources['preview'] = r'''
# -*- coding: utf-8 -*-
"""Temporary preview storage and Maya's cancellable save check, persistent across reloads."""
import os
import sys
import tempfile
import types
from maya import cmds
from maya.api import OpenMaya as om

STATE_NAME = "_yuejun_preview_state"
if STATE_NAME not in sys.modules:
    state = types.ModuleType(STATE_NAME)
    state.root = None
    state.active = False
    state.callbacks = []
    state.promoting = False
    sys.modules[STATE_NAME] = state
STATE = sys.modules[STATE_NAME]


def directory():
    if not STATE.root or not os.path.isdir(STATE.root):
        STATE.root = tempfile.mkdtemp(prefix="YuejunPreview_")
    install()
    return STATE.root


def mark(session):
    if session.preview:
        STATE.active = True


def promote():
    if not STATE.active or STATE.promoting:
        return
    from . import project
    project.require_project()
    STATE.promoting = True
    try:
        session = project.SyncSession()
        project.localize(session)
        scene = cmds.file(query=True, sceneName=True)
        if scene and STATE.root and project.inside(scene, STATE.root):
            local = session.copy_file(scene, "scene")
            cmds.file(rename=local)
        return session.summary()
    finally:
        STATE.promoting = False


def check_save(*_):
    if not STATE.active:
        return True
    from . import project
    try:
        root = project.require_project()
        promote()
        scene = cmds.file(query=True, sceneName=True)
        if not scene or not project.inside(scene, root):
            raise project.ProjectError("请将预览场景另存到当前项目内，不能保存到素材库或其他目录。")
        return True
    except Exception as error:
        cmds.warning("预览模式已阻止保存：请先设置有效项目。{}".format(error))
        return False


def after_scene(*_):
    from . import project
    scene = cmds.file(query=True, sceneName=True)
    STATE.active = bool(scene and STATE.root and project.inside(scene, STATE.root))


def after_save(*_):
    STATE.active = False


def install():
    if STATE.callbacks:
        return
    # Dispatch through the latest module after either package reload or single-script reload.
    name = __name__
    STATE.callbacks.append(om.MSceneMessage.addCheckCallback(
        om.MSceneMessage.kBeforeSaveCheck, lambda *args: sys.modules[name].check_save(*args)))
    for event in (om.MSceneMessage.kAfterNew, om.MSceneMessage.kAfterOpen):
        STATE.callbacks.append(om.MSceneMessage.addCallback(event, lambda *args: sys.modules[name].after_scene(*args)))
    STATE.callbacks.append(om.MSceneMessage.addCallback(
        om.MSceneMessage.kAfterSave, lambda *args: sys.modules[name].after_save(*args)))

'''

_yj_sources['project'] = r'''
# -*- coding: utf-8 -*-
"""Maya project validation, non-overwriting file sync and dependency remapping."""
import glob
import hashlib
import json
import os
import re
import shutil
import tempfile

from maya import cmds
from . import config, preview


class ProjectError(RuntimeError):
    pass


def inside(path, root):
    try:
        return os.path.normcase(os.path.commonpath((os.path.realpath(path), os.path.realpath(root)))) == os.path.normcase(os.path.realpath(root))
    except ValueError:
        return False


def root_directory():
    return os.path.realpath(cmds.workspace(query=True, rootDirectory=True))


def rule_directory(root, rule, default):
    value = default if preview.STATE.root and normalize(root) == normalize(preview.STATE.root) else (cmds.workspace(fileRuleEntry=rule) or default)
    path = os.path.realpath(value if os.path.isabs(value) else os.path.join(root, value))
    if not inside(path, root):
        raise ProjectError("项目规则 {} 指向项目之外：{}。请在项目窗口修改。".format(rule, path))
    return path


def require_project():
    root = root_directory()
    if not os.path.isfile(os.path.join(root, "workspace.mel")):
        raise ProjectError("请先在顶部“项目窗口”创建或设置 Maya 项目（需要 workspace.mel）。")
    default = os.path.realpath(os.path.join(cmds.internalVar(userAppDir=True), "projects", "default"))
    if os.path.normcase(root) == os.path.normcase(default):
        raise ProjectError("当前是 Maya 默认项目。请先在项目窗口创建自己的工作项目。")
    library = os.path.realpath(config.resource_root())
    if inside(root, library) or inside(library, root):
        raise ProjectError("工作项目和素材库不能相同或互相包含，请设置独立的项目目录。")
    for rule, fallback in (("scene", "scenes"), ("sourceImages", "sourceimages"),
                           ("images", "images"), ("renderData", "renderData")):
        rule_directory(root, rule, fallback)
    return root


def digest(path):
    result = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def normalize(path):
    return os.path.normcase(os.path.realpath(path))


class SyncSession(object):
    def __init__(self, source_scene=None):
        self.preview = False
        try:
            self.root = require_project()
        except ProjectError:
            self.preview = True
            self.root = preview.directory()
        self.library = os.path.realpath(config.resource_root())
        self.source_scene = source_scene
        self.copied = self.skipped = 0
        self.issues = []
        self.index_path = os.path.join(self.root, "data", "Yuejun", "sync_manifest.json")
        if not inside(self.index_path, self.root):
            raise ProjectError("项目同步记录目录指向项目之外。")
        self.index = {}
        if os.path.isfile(self.index_path):
            with open(self.index_path, "r", encoding="utf-8") as stream:
                self.index = json.load(stream)
            if not isinstance(self.index, dict):
                raise ProjectError("项目同步记录格式错误。")
        self._basenames = None

    def relative(self, path):
        return os.path.relpath(path, self.root).replace("\\", "/")

    def folder_destination(self, source, category):
        return os.path.dirname(self.destination(os.path.join(source, "__folder_anchor__"), category))

    def destination(self, source, category="texture"):
        rule, fallback = {"scene": ("scene", "scenes"), "texture": ("sourceImages", "sourceimages"),
                          "render": ("renderData", "renderData"), "cache": ("fileCache", "cache/nCache"),
                          "audio": ("sound", "sound"), "data": ("diskCache", "data")}[category]
        base = rule_directory(self.root, rule, fallback)
        if not self.preview and preview.STATE.root and inside(source, preview.STATE.root):
            preview_base = os.path.join(preview.STATE.root, fallback)
            relative = os.path.relpath(source, preview_base) if inside(source, preview_base) else os.path.join("Yuejun", "Preview", os.path.basename(source))
            result = os.path.realpath(os.path.join(base, relative))
            if not inside(result, self.root):
                raise ProjectError("预览资源目标位于项目之外。")
            return result
        if inside(source, self.library):
            relative = os.path.relpath(source, self.library)
            # Keep one recognizable Arnold directory under each Maya file rule.
            arnold = os.path.join("Maya_shader_node", "Arnold") + os.sep
            if relative.startswith(arnold):
                tail = relative[len(arnold):]
                for prefix in ("sourceimages" + os.sep, "renderData" + os.sep):
                    if tail.startswith(prefix):
                        tail = tail[len(prefix):]
                relative = os.path.join("Arnold", tail)
        else:
            parent_hash = hashlib.sha256(normalize(os.path.dirname(source)).encode("utf-8")).hexdigest()[:12]
            relative = os.path.join("External", parent_hash, os.path.basename(source))
        result = os.path.realpath(os.path.join(base, "Yuejun", relative))
        if not inside(result, self.root):
            raise ProjectError("同步目标超出了项目：" + result)
        return result

    def copy_file(self, source, category="texture", target_override=None):
        source = os.path.realpath(source)
        if not os.path.isfile(source):
            raise ProjectError("找不到资源：" + source)
        if inside(source, self.root):
            self.skipped += 1
            return source
        target = self.destination(source, category)
        key = normalize(source) + "|" + category
        previous = self.index.get(key, {})
        if not target_override and previous.get("target"):
            recorded = os.path.realpath(os.path.join(self.root, previous["target"]))
            if not inside(recorded, self.root):
                raise ProjectError("同步记录中的目标位于项目之外。")
            if os.path.isfile(recorded):
                target = recorded
        if target_override:
            target = os.path.realpath(target_override)
        if not inside(target, self.root):
            raise ProjectError("同步目标位于项目之外。")
        stat = os.stat(source)
        stamp = [stat.st_size, stat.st_mtime_ns]
        expected_old = None
        source_hash = None
        if os.path.isfile(target):
            if previous.get("source_stamp") == stamp and previous.get("target") == self.relative(target):
                # Existing project files belong to the artist, including their edits.
                self.skipped += 1
                return target
            source_hash = digest(source)
            target_hash = digest(target)
            if target_hash == source_hash or (previous.get("source_sha256") == source_hash and previous.get("target") == self.relative(target)):
                self.skipped += 1
            elif previous.get("target") == self.relative(target) and target_hash == previous.get("source_sha256") and "versions" not in os.path.relpath(target, self.root).split(os.sep):
                # Safe upgrade: this copy is still exactly the version we supplied.
                expected_old = target_hash
            else:
                # Keep artist edits; deduplicate the new source revision separately.
                base = self.destination(source, category)
                target = os.path.join(os.path.dirname(base), "versions", source_hash, os.path.basename(base))
                if not inside(target, self.root):
                    raise ProjectError("版本目录位于项目之外。")
                if os.path.isfile(target) and digest(target) != source_hash:
                    raise ProjectError("素材版本副本也已修改，请另存后重试：" + target)
                if os.path.isfile(target):
                    self.skipped += 1
        if not os.path.isfile(target) or expected_old is not None:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            # Write and validate a temporary sibling before replacing an unchanged old copy.
            with tempfile.NamedTemporaryFile(dir=os.path.dirname(target), prefix="sync_", suffix=".tmp", delete=False) as output:
                temp = output.name
            try:
                with open(temp, "wb") as output, open(source, "rb") as stream:
                    shutil.copyfileobj(stream, output, 8 * 1024 * 1024)
                source_hash = source_hash or digest(source)
                if digest(temp) != source_hash or [os.stat(source).st_size, os.stat(source).st_mtime_ns] != stamp:
                    raise ProjectError("素材在复制期间发生变化，请保存素材后重试：" + source)
                if expected_old is not None:
                    if not os.path.isfile(target) or digest(target) != expected_old:
                        raise ProjectError("项目文件在同步期间发生变化，未覆盖：" + target)
                    os.replace(temp, target)
                else:
                    # Windows rename refuses an existing target; never replace an unknown file.
                    if os.path.exists(target):
                        raise ProjectError("同步期间出现同名文件，请重试：" + target)
                    os.rename(temp, target)
            finally:
                if os.path.isfile(temp):
                    os.remove(temp)
            self.copied += 1
        self.index[key] = {"source_stamp": stamp, "source_sha256": source_hash, "target": self.relative(target)}
        self.flush()
        return target

    def flush(self):
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=os.path.dirname(self.index_path),
                                         prefix="sync_", suffix=".tmp", delete=False) as stream:
            temp = stream.name
            json.dump(self.index, stream, ensure_ascii=False, indent=2)
        try:
            os.replace(temp, self.index_path)
        finally:
            if os.path.isfile(temp):
                os.remove(temp)

    def resolve(self, raw):
        raw = os.path.expandvars(os.path.expanduser(raw.replace("\\", "/")))
        candidates = [raw] if os.path.isabs(raw) else [os.path.join(self.root, raw)]
        if self.source_scene:
            folder = os.path.dirname(self.source_scene)
            for _ in range(4):
                candidates.append(os.path.join(folder, raw))
                candidates.append(os.path.join(folder, "sourceimages", raw))
                folder = os.path.dirname(folder)
        for marker in ("Maya_Texture", "Maya_Light", "Maya_Model", "Maya_shader_node"):
            match = re.search(r"(?:^|/)" + marker + r"/(.*)$", raw, re.I)
            if match:
                candidates.append(os.path.join(self.library, marker, match.group(1)))
        for path in candidates:
            if pattern_files(path):
                return os.path.normpath(path)
        # Old supplied files can carry the author's obsolete absolute drive paths.
        if self._basenames is None:
            self._basenames = {}
            for folder, dirs, files in os.walk(self.library, followlinks=False):
                dirs[:] = [name for name in dirs if name not in ("_Backups", ".mayaSwatches") and
                           not os.path.islink(os.path.join(folder, name))]
                for name in files:
                    self._basenames.setdefault(name.lower(), []).append(os.path.join(folder, name))
        matches = self._basenames.get(os.path.basename(raw).lower(), [])
        if len(matches) == 1:
            return matches[0]
        raise ProjectError("资源不存在或位置不明确：" + raw)

    def resource(self, raw, category="texture", sequence=False):
        source = self.resolve(raw)
        if sequence and not has_pattern(source):
            source = re.sub(r"\d+(?=\.[^.]+$)", lambda m: "#" * len(m.group(0)), source)
        files = pattern_files(source)
        if not files:
            raise ProjectError("没有找到资源文件：" + source)
        copied_paths = []
        for path in files:
            copied_paths.append(self.copy_file(path, category))
            if category == "texture":
                sidecar = os.path.splitext(path)[0] + ".tx"
                if sidecar != path and os.path.isfile(sidecar):
                    self.copy_file(sidecar, category, target_override=os.path.splitext(copied_paths[-1])[0] + ".tx")
        if has_pattern(source):
            folders = {os.path.dirname(path) for path in copied_paths}
            if len(folders) > 1:
                # Keep UDIM/sequence filenames together even when one tile has artist edits.
                revision = hashlib.sha256("".join(digest(path) for path in files).encode("ascii")).hexdigest()
                folder = os.path.join(os.path.dirname(self.destination(source, category)), "versions", revision)
                for path in files:
                    self.copy_file(path, category, target_override=os.path.join(folder, os.path.basename(path)))
                    sidecar = os.path.splitext(path)[0] + ".tx"
                    if category == "texture" and os.path.isfile(sidecar):
                        self.copy_file(sidecar, category, target_override=os.path.join(folder, os.path.basename(sidecar)))
            else:
                folder = next(iter(folders))
            target = os.path.join(folder, os.path.basename(source))
        else:
            target = copied_paths[0]
        return target.replace("\\", "/") if self.preview else self.relative(target)

    def copy_tree(self, source, category):
        if not os.path.isdir(source):
            raise ProjectError("找不到资源目录：" + source)
        for folder, dirs, files in os.walk(source, followlinks=False):
            dirs[:] = [name for name in dirs if name != ".mayaSwatches" and not os.path.islink(os.path.join(folder, name))]
            for name in files:
                path = os.path.join(folder, name)
                if not os.path.islink(path):
                    self.copy_file(path, category)

    def bundle(self):
        """Copy supplied Arnold companion assets, including unconnected HDRI variants."""
        if not self.source_scene:
            return
        folder = os.path.dirname(self.source_scene)
        if os.path.isfile(os.path.join(folder, "manifest.json")):
            for name, category in (("sourceimages", "texture"), ("renderData", "render")):
                path = os.path.join(folder, name)
                if os.path.isdir(path):
                    self.copy_tree(path, category)

    def summary(self):
        return ("未设置有效项目：临时预览，设置项目之前禁止保存。" if self.preview else "") + "复制 {} 个文件，复用 {} 个已有文件，{} 项需检查。".format(self.copied, self.skipped, len(self.issues))


def has_pattern(path):
    return bool(re.search(r"<UDIM>|<UVTILE>|<f\d*>|<frame>|#+|%0?\d*d", path, re.I))


def pattern_files(path):
    pattern = re.sub(r"<UDIM>", "[0-9][0-9][0-9][0-9]", path, flags=re.I)
    pattern = re.sub(r"<UVTILE>", "u[0-9]*_v[0-9]*", pattern, flags=re.I)
    pattern = re.sub(r"<f\d*>|<frame>|%0?\d*d", "*", pattern, flags=re.I)
    pattern = re.sub(r"#+", lambda m: "[0-9]" * len(m.group(0)), pattern)
    if pattern == path:
        return [path] if os.path.isfile(path) else []
    return sorted(path for path in glob.glob(pattern) if os.path.isfile(path))


# FilePathEditor covers registered plug-in attributes; these cover common omissions.
PATH_ATTRIBUTES = {"fileTextureName": "texture", "filename": "texture", "fileName": "texture",
                   "dso": "cache", "abc_File": "cache", "cacheFileName": "cache",
                   "aiFilename": "texture", "xgFileName": "data", "iesFile": "texture"}


def selected_node(node, nodes):
    return nodes is None or bool(set(cmds.ls(node, long=True) or []).intersection(cmds.ls(nodes, long=True) or []))


def cache_dependencies(nodes=None):
    result = []
    for node in cmds.ls(type="cacheFile") or []:
        if selected_node(node, nodes):
            directory = cmds.getAttr(node + ".cachePath") or ""
            name = cmds.getAttr(node + ".cacheName") or ""
            if directory and name:
                result.append((node, directory, name))
    return result


def localize_references(session, nodes):
    # Only references brought by this operation; don't reload pre-existing artist references.
    visited = set()
    for _ in range(32):
        pending = [ref for ref in (cmds.ls(type="reference") or []) if ref not in visited and
                   ref != "sharedReferenceNode" and selected_node(ref, nodes)]
        if not pending:
            return
        for ref in pending:
            visited.add(ref)
            try:
                raw = cmds.referenceQuery(ref, filename=True, withoutCopyNumber=True)
                source = session.resolve(raw)
                target = session.copy_file(source, "scene")
                if not cmds.referenceQuery(ref, isLoaded=True):
                    session.issues.append("未加载的引用无法检查内部资源：" + raw)
                    continue
                if normalize(source) != normalize(target):
                    cmds.file(target, loadReference=ref, executeScriptNodes=False)
                if nodes is not None:
                    nodes.extend(cmds.referenceQuery(ref, nodes=True, dagPath=True) or [])
            except Exception as error:
                session.issues.append("引用 {}：{}".format(ref, error))
    session.issues.append("引用层级超过检查上限，请检查嵌套引用。")


def dependencies(nodes=None):
    allowed = set(cmds.ls(nodes, long=True) or []) if nodes else (set() if nodes is not None else None)
    result = {}
    errors = []
    def add(plug, category="texture"):
        node = plug.split(".", 1)[0]
        if allowed is not None and not allowed.intersection(cmds.ls(node, long=True) or []):
            return
        try:
            if cmds.getAttr(plug, type=True) != "string":
                return
            value = cmds.getAttr(plug)
            if value:
                if plug.rsplit(".", 1)[-1] == "cachePath":
                    return  # nCache's directory plus cacheName is handled together.
                if category == "data":
                    extension = os.path.splitext(value)[1].lower()
                    if extension in (".exr", ".tx", ".tif", ".tiff", ".jpg", ".jpeg", ".png", ".hdr", ".tga", ".bmp", ".ies"):
                        category = "texture"
                    elif extension in (".abc", ".vdb", ".ass", ".mcx", ".mc"):
                        category = "cache"
                result[plug] = (value, "audio" if cmds.nodeType(node) == "audio" else category)
        except Exception as error:
            errors.append("无法检查 {}：{}".format(plug, error))
    try:
        cmds.filePathEditor(refresh=True)
        for folder in cmds.filePathEditor(query=True, listDirectories="") or []:
            entries = cmds.filePathEditor(query=True, listFiles=folder, withAttribute=True) or []
            for index in range(1, len(entries), 2):
                plug = entries[index]
                if "." in plug and cmds.objExists(plug):
                    add(plug, PATH_ATTRIBUTES.get(plug.rsplit(".", 1)[-1], "data"))
    except Exception as error:
        errors.append("文件路径编辑器扫描失败：{}".format(error))
    for attribute, category in PATH_ATTRIBUTES.items():
        for plug in cmds.ls("*." + attribute, recursive=True) or []:
            if attribute in ("filename", "fileName") and cmds.nodeType(plug.split(".", 1)[0]) not in ("aiImage", "audio", "mentalrayTexture"):
                continue
            add(plug, category)
    return result, errors


def localize(session, nodes=None):
    """Remap only newly imported nodes, or the just-opened preset scene."""
    nodes = list(nodes) if nodes is not None else None
    localize_references(session, nodes)
    paths, errors = dependencies(nodes)
    session.issues.extend(errors)
    for plug, (raw, category) in paths.items():
        try:
            node = plug.split(".", 1)[0]
            sequence = False
            if cmds.nodeType(node) == "file":
                sequence = bool(cmds.getAttr(node + ".useFrameExtension"))
                if cmds.getAttr(node + ".uvTilingMode") and not has_pattern(raw):
                    raw = re.sub(r"(?<!\d)1\d{3}(?=\.[^.]+$)", "<UDIM>", raw)
            mapped = session.resource(raw, category, sequence)
            if mapped != raw:
                if cmds.getAttr(plug, lock=True):
                    raise ProjectError("属性已锁定")
                cmds.setAttr(plug, mapped, type="string")
        except Exception as error:
            session.issues.append("{}：{}".format(plug, error))
    for node, folder, name in cache_dependencies(nodes):
        try:
            folder = folder if os.path.isabs(folder) else os.path.join(session.root, folder)
            files = [path for path in glob.glob(os.path.join(folder, glob.escape(name) + "*"))
                     if os.path.isfile(path) and os.path.splitext(path)[1].lower() in (".xml", ".mcx", ".mc")]
            if not files:
                raise ProjectError("缺少 nCache 文件：" + os.path.join(folder, name))
            for path in files:
                session.copy_file(path, "cache")
            target = folder if inside(folder, session.root) else session.folder_destination(folder, "cache")
            cmds.setAttr(node + ".cachePath", target.replace("\\", "/"), type="string")
        except Exception as error:
            session.issues.append("{}：{}".format(node, error))
    # Arnold RenderView stores its snapshot directory inside a settings string.
    for plug in cmds.ls("*.ARV_options", recursive=True) or []:
        if not selected_node(plug.split(".", 1)[0], nodes):
            continue
        raw = cmds.getAttr(plug) or ""
        match = re.search(r"Snapshots Folder=([^;]+)", raw)
        if match:
            source = match.group(1)
            if os.path.isdir(source):
                try:
                    session.copy_tree(source, "render")
                    target = source if inside(source, session.root) else session.folder_destination(source, "render")
                    cmds.setAttr(plug, raw[:match.start(1)] + target.replace("\\", "/") + raw[match.end(1):], type="string")
                except Exception as error:
                    session.issues.append("{}：{}".format(plug, error))
    for issue in session.issues:
        cmds.warning(issue)
    return session.summary()


def audit():
    root = root_directory()
    issues = []
    try:
        require_project()
    except Exception as error:
        issues.append(str(error))
    for rule in cmds.workspace(query=True, fileRuleList=True) or []:
        value = cmds.workspace(fileRuleEntry=rule)
        if value:
            path = value if os.path.isabs(value) else os.path.join(root, value)
            if not inside(path, root):
                issues.append("项目规则位于项目外：{} → {}".format(rule, value))
    for rule, default in (("scene", "scenes"), ("sourceImages", "sourceimages")):
        try:
            path = rule_directory(root, rule, default)
            if not os.path.isdir(path):
                issues.append("项目目录尚不存在：" + path)
        except ProjectError:
            pass
    scene = cmds.file(query=True, sceneName=True)
    if not scene:
        issues.append("当前场景尚未保存到项目。")
    elif not inside(scene, root):
        issues.append("当前场景保存在项目外：" + scene)
    if cmds.file(query=True, modified=True):
        issues.append("当前场景有未保存修改；请保存以保留资源路径更新。")
    paths, scan_errors = dependencies()
    issues.extend(scan_errors)
    for reference in cmds.file(query=True, reference=True) or []:
        paths["场景引用 " + reference] = (re.sub(r"\{\d+\}$", "", reference), "scene")
    for ref in cmds.ls(type="reference") or []:
        if ref == "sharedReferenceNode":
            continue
        try:
            if not cmds.referenceQuery(ref, isLoaded=True):
                issues.append("未加载引用的内部资源未检查：" + ref)
        except Exception as error:
            issues.append("无法检查引用 {}：{}".format(ref, error))
    for node, folder, name in cache_dependencies():
        paths[node + ".cachePath"] = (os.path.join(folder, name + ".xml"), "cache")
    for plug, (raw, _) in paths.items():
        expanded = os.path.expandvars(os.path.expanduser(raw.replace("\\", "/")))
        path = expanded if os.path.isabs(expanded) else os.path.join(root, expanded)
        if not inside(path, root):
            issues.append("项目外资源：{} → {}".format(plug, raw))
        if not pattern_files(path):
            issues.append("缺失资源：{} → {}".format(plug, raw))
        if os.path.splitext(raw)[1].lower() in (".xgen", ".ass", ".usd", ".usda", ".usdc"):
            issues.append("复合资源内部依赖需在对应插件中确认：{} → {}".format(plug, raw))
    for plug in cmds.ls("*.ARV_options", recursive=True) or []:
        match = re.search(r"Snapshots Folder=([^;]+)", cmds.getAttr(plug) or "")
        if match and not inside(match.group(1), root):
            issues.append("项目外快照目录：" + match.group(1))
    unknown = cmds.ls(type="unknown") or []
    if unknown:
        issues.append("存在未知节点，其资源无法完整检查：" + "、".join(unknown))
    return "当前项目：{}\n检查了 {} 个资源路径。\n{}".format(
        root, len(paths), "\n".join(issues) if issues else "检查通过：已检查的资源均位于项目内且存在。") + \
        "\n\n检查范围：Maya 文件路径编辑器注册资源、常用贴图 / 缓存 / 音频、场景引用和 RenderView 快照。未注册插件的私有路径可能需要插件自身检查。"

'''

_yj_sources['core'] = r'''
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


def rename_target():
    """Original BS preparation command: rename the first selected object."""
    selected = cmds.ls(selection=True)
    if selected:
        actual = cmds.rename(selected[0], "Mubiao")
        return "Successfully renamed the model to {}.".format(actual)
    return "No objects selected."


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
        raise ToolError("找不到 {}，请先安装 GN 并将其脚本加入 Maya 路径。".format(procedure))
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
    if tool.kind in ("mel", "import", "open", "legacy_import", "legacy_mel"):
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


def execute(key):
    tool = config.TOOLS.get(key)
    if tool is None:
        raise ToolError("未知工具：{}".format(key))
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
    actions = {"rename_target": rename_target, "vray_skin": configure_vray_skin,
               "restore_xgen_guides": restore_xgen_guides,
               "clean_unknown_nodes": clean_unknown_nodes}
    return actions[key]()

'''

_yj_sources['eyes'] = r'''
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
        source = config.asset_path("Maya_Model/Eye_Arnold/sourceimages/" + relative)
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

'''

_yj_sources['notes_data'] = r'''
# -*- coding: utf-8 -*-
"""User-supplied reference notes. Expressions are text, never executed by the tool."""
NOTES = [
    dict(title='Width · 贴图控制宽度', language='XGen',
         usage='在 Width 创建 Mask，再打开表达式编辑器。保留 Maya 为你生成的 map 路径，将下方 longhair_width_mask 替换为实际名称。\n\n遮罩值为 0～1 时，乘以 0.02 得到 0～0.02 的宽度。若贴图超出此范围，乘法本身不会强制钳制上限。',
         code="$a=map('${DESC}/paintmaps/longhair_width_mask');#3dpaint,20.0\n$a*0.02"),
    dict(title='Noise · 随机百分比 13%', language='XGen',
         usage='粘贴到需要随机黑白遮罩的表达式栏，例如 Noise 的 Mask。percentStray 的范围注释会提供 0～100 的滑块。\n\n输出为 0 或 1；百分比代表概率，小量毛发的实际比例不一定精确等于设定值。',
         code='$percentStray=13.0000;#0.00,100\nrand() < $percentStray/100.0 ? 1 : 0'),
    dict(title='Noise · 随机百分比 80%', language='XGen',
         usage='与 13% 条目相同，这里将初始比例设为 80%。可按需要修改数值。',
         code='$percentStray=80; #0,100\nrand() < $percentStray/100.0 ? 1 : 0'),
    dict(title='Cut · 按长度随机修剪', language='XGen',
         usage='用于 Cut 修改器的 Amount（修剪长度）表达式栏。虽然原笔记标题写作 Cut Mask，但该式输出的是长度，不是单纯的 0～1 遮罩。\n\n随机比例乘以 $cLength：同一比例下，越长的毛发切掉的绝对长度越大。',
         code='$cut=rand(0,1);\n$cut*$cLength'),
    dict(title='Coil · 百分比与随机种子', language='XGen',
         usage='用于 Coil 的遮罩表达式。percentage 控制随机选中的比例，percentageSeed 控制随机分布；修改种子可换一组毛发。',
         code='$percentage=10;#0,100\n$percentageSeed=5;#0,20\n$randvalue=rand(0,1,$percentageSeed);\n$randvalue<$percentage/100? 1 : 0'),
    dict(title='Mask · 绘制遮罩叠加百分比', language='XGen · 追加片段',
         usage='先创建并绘制 Mask，保留编辑器原有的 $a=map(...) 那一行，再追加下方代码。\n\n代码故意不包含 map 行，不要删除已有定义。如果原来的变量不叫 $a，请同步修改代码中的 $a。白色区域使用完整设定比例，灰色按比例降低，黑色不选中。',
         code='$percentStray=100.0000; #0.00,100\nrand() < ($percentStray*$a) /100.0? 1:0'),
    dict(title='Color · Salt and Pepper', language='XGen',
         usage='新建名为 random 的颜色自定义参数，将 MAPNAME 替换为你绘制的颜色贴图名称；保留实际 map 路径。\n\n可在基本体颜色中查看效果。Arnold 材质使用 aiUserDataColor 时，将其 Attribute 对应到导出的 random 颜色属性。还需确认该参数实际随 XGen 导出。\n\n此条保留原笔记算法，包括 $noise2 的加法。结果可能超出 0～1，亮度和随机比例的视觉效果请在实际材质中检查。',
         code="$hairMap = map('${DESC}/paintmaps/custom_color_MAPNAME');#3dpaint,50.0\n$percentStrand = 75; #0,100\n$colour = [1,1,1]; #colour\n\n$percentRand=rand() < $percentStrand/100 ? 0:1;\n$noise=$percentRand*$colour;\n$white = $noise + $hairMap;\n\n$percentStrand2 = 20; #0,100\n$colour2 = [0.027451,0.0196078,0.00392157]; #colour\n$percentRand2=rand() < $percentStrand2/100 ? 0:1;\n$noise2=$percentRand2+$colour2;\n\n$white * $noise2"),
    dict(title='stray · 偏离毛发条件', language='XGen',
         usage='先设置 Description 的 Stray 百分比，再使用条件表达式。stray()? X : Y 表示：偏离毛发返回 X，其余返回 Y。\n\n下面使用可直接复制的数值示例：偏离毛发为 1，其余为 0。可用于 Noise 等需要区分两类毛发的参数。\n\n原笔记参考链接（未对网页内容作验证）：\nhttps://www.bilibili.com/read/cv12015260/',
         code='stray()? 1 : 0'),
    dict(title='rand · 最小值与最大值', language='XGen',
         usage='rand(最小值, 最大值) 返回范围内的随机数。下面示例为 0～1。',
         code='rand(0,1)'),
    dict(title='Length · 长度比例', language='XGen',
         usage='用毛发长度乘以比例。Maya 2022 自带 XGen 提示使用 $cLength，L 必须大写；已修正原笔记中的 $clength。',
         code='$cLength*0.001'),
    dict(title='clamp · 限制长度范围', language='XGen',
         usage='clamp(x, min, max) 将结果限制到最小值与最大值之间。下面把长度乘以 0.001 后限制在 0.005～0.1。\n\n$cLength 的 L 为大写。',
         code='clamp($cLength*0.001,0.005,0.1)'),
    dict(title='MEL · 清理未知节点（原笔记）', language='MEL · 会删除节点',
         usage='这是 MEL，不是 XGen 表达式。若手动执行，应粘贴到 Script Editor 的 MEL 页签。\n\n原笔记会解锁并删除所有 unknown 节点，还会移除未知插件记录；包含缺失插件的数据也可能被删除。一般优先使用工具箱现有的“清理无效节点”，它会跳过引用和锁定节点。这里仅提供查看和复制，不自动执行。',
         code='string $unknownNodes[] = `ls -type "unknown"`;\n\nfor($node in $unknownNodes) {\n    print("Deleting " + $node + "\\n");\n    lockNode -lock 0 $node;\n    delete $node;\n}\n\nstring $plugin;\nstring $unknownPlugins[] = `unknownPlugin -query -list`;\nfor ($plugin in $unknownPlugins) {\n    unknownPlugin -remove $plugin;\n}')
]


def search(query):
    query = query.strip().lower()
    return [item for item in NOTES if query in (item['title'] + ' ' + item['usage']).lower()]

'''

_yj_sources['notes'] = r'''
# -*- coding: utf-8 -*-
"""Read/copy-only reference UI, separate from the note catalogue and scene logic."""
from maya import cmds
from . import notes_data

WINDOW = 'yuejunExpressionNotes'
_instance = None


class NotesWindow(object):
    def build(self):
        window = cmds.window(WINDOW, title='XGen 表达式速查', widthHeight=(900, 620), sizeable=True)
        root = cmds.formLayout(parent=window)
        self.search_field = cmds.textField(parent=root, placeholderText='搜索名称或用途…',
                                           height=28, changeCommand=self.filter)
        self.list = cmds.textScrollList(parent=root, allowMultiSelection=False,
                                        selectCommand=self.select)
        detail = cmds.formLayout(parent=root)
        self.title = cmds.text(parent=detail, label='', align='left', font='boldLabelFont', height=26)
        self.usage = cmds.scrollField(parent=detail, editable=False, wordWrap=True)
        hint = cmds.text(parent=detail, label='代码可临时修改；复制当前内容后，粘贴到对应的表达式栏。',
                         align='left', height=24)
        self.code = cmds.scrollField(parent=detail, editable=True, wordWrap=False, font='fixedWidthFont')
        buttons = cmds.formLayout(parent=detail, height=34)
        copy = cmds.button(parent=buttons, label='复制代码', command=self.copy,
                           backgroundColor=(0.23, 0.39, 0.43))
        reset = cmds.button(parent=buttons, label='恢复此条原文', command=self.select)
        cmds.formLayout(buttons, edit=True,
                        attachForm=[(copy, 'left', 0), (reset, 'right', 0)] +
                                   [(b, edge, 0) for b in (copy, reset) for edge in ('top', 'bottom')],
                        attachPosition=[(copy, 'right', 4, 50), (reset, 'left', 4, 50)])
        self.status = cmds.text(parent=detail, label='只查看和复制，不会自动修改场景。', align='left', height=24)
        cmds.formLayout(detail, edit=True,
                        attachForm=[(c, edge, 0) for c in (self.title, self.usage, hint, self.code, buttons, self.status)
                                    for edge in ('left', 'right')] + [(self.title, 'top', 0), (self.status, 'bottom', 0)],
                        attachPosition=[(self.usage, 'bottom', 0, 37)],
                        attachControl=[(self.usage, 'top', 8, self.title), (hint, 'top', 8, self.usage),
                                       (self.code, 'top', 8, hint), (self.code, 'bottom', 8, buttons),
                                       (buttons, 'bottom', 8, self.status)])
        cmds.formLayout(root, edit=True,
                        attachForm=[(self.search_field, 'left', 12), (self.search_field, 'top', 12),
                                    (self.list, 'left', 12), (self.list, 'bottom', 12),
                                    (detail, 'top', 12), (detail, 'right', 12), (detail, 'bottom', 12)],
                        attachPosition=[(self.search_field, 'right', 4, 30), (self.list, 'right', 4, 30)],
                        attachControl=[(self.list, 'top', 8, self.search_field), (detail, 'left', 8, self.list)])
        self.filter()
        cmds.showWindow(window)
        return window

    def filter(self, *_):
        self.items = notes_data.search(cmds.textField(self.search_field, query=True, text=True))
        cmds.textScrollList(self.list, edit=True, removeAll=True)
        if self.items:
            cmds.textScrollList(self.list, edit=True, append=[item['title'] for item in self.items], selectIndexedItem=1)
        self.select()

    def select(self, *_):
        selected = cmds.textScrollList(self.list, query=True, selectIndexedItem=True) or []
        item = self.items[selected[0] - 1] if selected else None
        cmds.text(self.title, edit=True, label=(item['title'] + '  |  ' + item['language']) if item else '没有匹配的笔记')
        cmds.scrollField(self.usage, edit=True, text=item['usage'] if item else '请修改搜索关键词。')
        cmds.scrollField(self.code, edit=True, text=item['code'] if item else '')
        cmds.text(self.status, edit=True, label='临时修改不会保存；切换条目会恢复原文。')

    def copy(self, *_):
        text = cmds.scrollField(self.code, query=True, text=True)
        if not text.strip():
            cmds.text(self.status, edit=True, label='没有可复制的代码。')
            return
        try:
            from PySide2.QtWidgets import QApplication
            app = QApplication.instance()
            if app is None:
                raise RuntimeError('Maya 界面尚未初始化')
            app.clipboard().setText(text)
            cmds.text(self.status, edit=True, label='已复制代码。请粘贴到对应位置；工具未执行代码。')
        except Exception as error:
            cmds.warning('无法访问剪贴板：{}。可在代码框中全选并按 Ctrl+C。'.format(error))


def close():
    global _instance
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW, window=True)
    _instance = None


def show():
    global _instance
    close()
    _instance = NotesWindow()
    try:
        return _instance.build()
    except Exception:
        close()
        raise

'''

_yj_sources['ui'] = r'''
# -*- coding: utf-8 -*-
"""maya.cmds UI and exception boundary. Core logic lives in core.py."""
import logging
from functools import partial

from maya import cmds, mel

from . import config, core, project, eyes, preview

WINDOW = "yuejunToolboxWindow"
_instance = None
GAP = 8
BUTTON_HEIGHT = 34
ACCENT = (0.23, 0.39, 0.43)
_LOG = logging.getLogger("yuejun_toolbox")


class ToolboxWindow(object):
    def __init__(self):
        self.buttons = {}
        self.busy = False
        self.path_field = None
        self.status = None
        self.vray_mode = False

    def build(self):
        config.migrate_preferences()
        window = cmds.window(WINDOW, title="Yuejun Toolbox 3.7.2",
                             widthHeight=(540, 770), sizeable=True)
        root = cmds.formLayout(parent=window)
        header = cmds.columnLayout(parent=root, adjustableColumn=True, rowSpacing=GAP)
        self.section(header, *config.PROJECT_GROUP, prominent=True)
        mode = cmds.columnLayout(parent=header, adjustableColumn=True, rowSpacing=4)
        cmds.checkBox(parent=mode, label="使用 V-Ray（默认 Arnold）", height=24,
                      value=False, changeCommand=self.switch_renderer)
        cmds.text(parent=mode, label="未设置项目可预览；设置项目后才能保存", align="left", height=20)
        settings = cmds.frameLayout(parent=header, label="资源与工具设置", collapsable=True,
                                    collapse=True, marginWidth=GAP, marginHeight=GAP)
        settings_column = cmds.columnLayout(parent=settings, adjustableColumn=True, rowSpacing=GAP)
        self.path_field = cmds.textFieldButtonGrp(
            parent=settings_column, label="资源目录", text=config.resource_root(),
            buttonLabel="选择…", adjustableColumn=2, columnWidth3=(60, 300, 60),
            buttonCommand=self.choose_root, changeCommand=self.save_root)
        row = cmds.formLayout(parent=settings_column, height=BUTTON_HEIGHT)
        refresh = cmds.button(parent=row, label="刷新资源", command=self.refresh)
        reload_button = cmds.button(parent=row, label="重载工具", command=self.reload)
        self.equal_columns(row, [refresh, reload_button])
        # GN stays visible while the remaining tools scroll.
        gn = self.section(root, *config.GROUPS[0], prominent=True)
        scroll = cmds.scrollLayout(parent=root, childResizable=True)
        self.body = cmds.columnLayout(parent=scroll, adjustableColumn=True, rowSpacing=8)
        self.render_body()
        self.status = cmds.text(parent=root, label="就绪", align="left", wordWrap=True, height=40)
        cmds.formLayout(root, edit=True,
                        attachForm=[(header, "top", 8), (header, "left", 12), (header, "right", 12),
                                    (gn, "left", 12), (gn, "right", 12),
                                    (scroll, "left", 12), (scroll, "right", 12),
                                    (self.status, "left", 12), (self.status, "right", 12),
                                    (self.status, "bottom", 8)],
                        attachControl=[(gn, "top", GAP, header), (scroll, "top", 8, gn),
                                       (scroll, "bottom", 8, self.status)])
        self.refresh()
        cmds.showWindow(window)
        return window

    def render_body(self):
        for child in cmds.columnLayout(self.body, query=True, childArray=True) or []:
            cmds.deleteUI(child)
        pinned = {tool.key for tool in config.PROJECT_GROUP[1]} | {tool.key for tool in config.GROUPS[0][1]}
        self.buttons = {key: button for key, button in self.buttons.items() if key in pinned}
        for title, tools in config.visible_groups(self.vray_mode)[1:]:
            self.section(self.body, title, tools)

    def switch_renderer(self, value, *_):
        self.vray_mode = bool(value)
        self.render_body()
        self.refresh()

    @staticmethod
    def equal_columns(row, controls, columns=None):
        """Percentage attachments keep every button in the row equally wide."""
        positions = []
        edges = []
        count = columns or len(controls)
        for index, control in enumerate(controls):
            edges.extend([(control, "top", 0), (control, "bottom", 0)])
            positions.extend([(control, "left", 0 if index == 0 else GAP // 2, index * 100 // count),
                              (control, "right", 0 if index == count - 1 else GAP // 2, (index + 1) * 100 // count)])
        cmds.formLayout(row, edit=True, attachForm=edges, attachPosition=positions)

    def section(self, parent, title, tools, prominent=False):
        frame = cmds.frameLayout(parent=parent, label=title, collapsable=not prominent,
                                 marginWidth=GAP, marginHeight=GAP)
        column = cmds.columnLayout(parent=frame, adjustableColumn=True, rowSpacing=GAP)
        if title == "眼球" and not self.vray_mode:
            row = cmds.formLayout(parent=column, height=BUTTON_HEIGHT)
            self.eye_color = cmds.optionMenu(parent=row, label="Arnold 颜色")
            for label, value in eyes.COLORS:
                cmds.menuItem(parent=self.eye_color, label=label)
            self.eye_resolution = cmds.optionMenu(parent=row, label="贴图精度")
            for value in eyes.RESOLUTIONS:
                cmds.menuItem(parent=self.eye_resolution, label=value)
            cmds.optionMenu(self.eye_resolution, edit=True, value="2k")
            self.equal_columns(row, [self.eye_color, self.eye_resolution])
        columns = config.GROUP_COLUMNS.get(title, 2)
        for start in range(0, len(tools), columns):
            row = cmds.formLayout(parent=column, height=BUTTON_HEIGHT)
            controls = []
            for tool in tools[start:start + columns]:
                options = {"backgroundColor": ACCENT} if prominent else {}
                button = cmds.button(parent=row, label=tool.label, annotation=tool.help,
                                     command=partial(self.run, tool.key), **options)
                self.buttons[tool.key] = button
                controls.append(button)
            self.equal_columns(row, controls, columns if len(tools) > columns else len(controls))
        if title == "眼球" and not self.vray_mode:
            cmds.button(parent=column, label="将设置应用到所选 Arnold 眼球", height=BUTTON_HEIGHT,
                        command=self.apply_eye_settings)
            cmds.text(parent=column, label="精度指贴图分辨率；共用材质的眼球会一起更新。", align="left", height=20)
        return frame

    def eye_settings(self):
        color = dict(eyes.COLORS)[cmds.optionMenu(self.eye_color, query=True, value=True)]
        resolution = cmds.optionMenu(self.eye_resolution, query=True, value=True)
        return color, resolution

    def apply_eye_settings(self, *_):
        if self.busy:
            return
        self.busy = True
        try:
            result = self.guarded(lambda: eyes.apply(*self.eye_settings()))
            if result:
                self.message(result)
        finally:
            self.busy = False

    def message(self, text, error=False):
        if self.status and cmds.text(self.status, exists=True):
            cmds.text(self.status, edit=True, label=text)
        if error:
            cmds.warning(text)
        else:
            print("[Yuejun Toolbox] " + text)

    def guarded(self, action):
        try:
            return action()
        except (core.ToolError, project.ProjectError, ValueError, OSError) as error:
            self.message(str(error), error=True)
        except Exception as error:
            _LOG.exception("Yuejun Toolbox operation failed")
            self.message("操作失败：{}。详细信息见 Script Editor。".format(error), error=True)
        return None

    def choose_root(self, *_):
        def choose():
            folders = cmds.fileDialog2(fileMode=3, dialogStyle=2, caption="选择工具箱资源根目录")
            if folders:
                config.set_resource_root(folders[0])
                self.refresh()
        return self.guarded(choose)

    def save_root(self, *_):
        def save():
            config.set_resource_root(cmds.textFieldButtonGrp(self.path_field, query=True, text=True))
            self.refresh()
        return self.guarded(save)

    def refresh(self, *_):
        def update():
            cmds.textFieldButtonGrp(self.path_field, edit=True, text=config.resource_root())
            missing = []
            for key, button in self.buttons.items():
                available, hint = core.availability(config.TOOLS[key])
                cmds.button(button, edit=True, enable=available, annotation=hint)
                if not available:
                    missing.append(config.TOOLS[key].label)
            self.message("缺少资源，相关按钮已禁用：" + "、".join(missing) if missing else
                         "资源检查通过。GN / 渲染器依赖在执行时检查。")
        return self.guarded(update)

    def run(self, key, *_):
        if self.busy:
            return
        if key == "expression_notes":
            from . import notes
            return self.guarded(notes.show)
        if key == "project_window":
            return self.guarded(lambda: mel.eval("projectWindow;"))
        if key == "set_project":
            return self.guarded(self.set_project)
        if key == "check_project":
            return self.guarded(self.check_project)
        if config.TOOLS[key].kind == "legacy_mel":
            self.busy = True
            def schedule():
                cmds.evalDeferred(partial(self.run_deferred_legacy, key))
                return True
            if not self.guarded(schedule):
                self.busy = False
            return
        self.busy = True
        try:
            if config.TOOLS[key].kind in ("open", "import", "legacy_import", "copy"):
                self.message("正在同步到当前项目，首次复制大贴图可能需要一些时间…")
                cmds.refresh()
            if key == "import_eye_arnold":
                action = lambda _: eyes.import_eye(*self.eye_settings())
            else:
                action = self.open_preset if config.TOOLS[key].kind == "open" else core.execute
            result = self.guarded(partial(action, key))
            if result:
                self.message(result)
        finally:
            self.busy = False

    def run_deferred_legacy(self, key):
        try:
            # A queued callback from a closed/reloaded window must not edit a scene.
            if _instance is not self or not cmds.window(WINDOW, exists=True):
                return
            result = self.guarded(partial(core.execute, key))
            if result:
                self.message(result)
        finally:
            self.busy = False

    def open_preset(self, key):
        tool = config.TOOLS[key]
        # Resolve prerequisites before asking the user to save or discard anything.
        core.require_renderer(core.require_file(tool.path))
        discard = False
        if core.scene_modified():
            choice = cmds.confirmDialog(
                title="打开场景预设", message="打开预设将替换当前场景。是否保存当前修改？",
                button=["保存并打开", "不保存并打开", "取消"],
                defaultButton="保存并打开", cancelButton="取消", dismissString="取消")
            if choice == "取消":
                return "已取消打开预设。"
            if choice == "保存并打开":
                if cmds.file(query=True, sceneName=True):
                    core.save_scene()
                else:
                    paths = cmds.fileDialog2(fileMode=0, dialogStyle=2, caption="保存当前场景",
                                             fileFilter="Maya ASCII (*.ma);;Maya Binary (*.mb)")
                    if not paths:
                        return "已取消保存，未打开预设。"
                    core.save_scene(paths[0])
            elif choice == "不保存并打开":
                discard = True
            else:
                return "已取消打开预设。"
        return core.open_scene_preset(tool.path, discard_changes=discard)

    def set_project(self):
        mel.eval('setProject "";')
        if preview.STATE.active:
            try:
                project.require_project()
            except project.ProjectError:
                return self.message("仍处于预览模式：尚未设置有效项目。")
            result = preview.promote()
            self.message("已设置项目。" + (result or "") + "现在可将场景保存在项目内。")
        else:
            self.message("当前项目：" + project.root_directory())

    def check_project(self):
        report = project.audit()
        name = "yuejunProjectReport"
        if cmds.window(name, exists=True):
            cmds.deleteUI(name)
        window = cmds.window(name, title="当前 Maya 项目检查", widthHeight=(780, 500))
        layout = cmds.formLayout(parent=window)
        field = cmds.scrollField(parent=layout, text=report, editable=False, wordWrap=False)
        cmds.formLayout(layout, edit=True, attachForm=[(field, edge, 10) for edge in ("top", "left", "right", "bottom")])
        cmds.showWindow(window)
        print(report)
        return report

    def reload(self, *_):
        def reload_now():
            from . import reload_toolbox
            return reload_toolbox()
        return self.guarded(reload_now)


def close():
    global _instance
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW, window=True)
    _instance = None
    from . import notes
    notes.close()
    if cmds.window("yuejunProjectReport", exists=True):
        cmds.deleteUI("yuejunProjectReport")


def show():
    global _instance
    close()
    _instance = ToolboxWindow()
    try:
        return _instance.build()
    except Exception as error:
        close()
        _LOG.exception("Unable to create Yuejun Toolbox")
        cmds.warning("工具箱界面创建失败：{}".format(error))
        return None

'''

def _yj_launch(sources=_yj_sources, sys=_yj_sys, types=_yj_types):
    from maya import cmds
    for name in ("yuejun_toolbox.ui", "_yuejun_single.ui"):
        previous = sys.modules.get(name)
        if previous is not None:
            previous.close()
    for window in ("yuejunToolbox", "myWindow"):
        if cmds.window(window, exists=True):
            cmds.deleteUI(window)
    package_name = "_yuejun_single"
    package = types.ModuleType(package_name)
    package.__path__ = []
    package.__package__ = package_name
    package.__version__ = "3.7.2"
    sys.modules[package_name] = package
    for name in ("config", "preview", "project", "core", "eyes", "notes_data", "notes", "ui"):
        fullname = package_name + "." + name
        module = types.ModuleType(fullname)
        module.__package__ = package_name
        module.__file__ = "<Yuejun single script/" + name + ".py>"
        sys.modules[fullname] = module
        setattr(package, name, module)
        exec(compile(sources[name], module.__file__, "exec"), module.__dict__)
    package.reload_toolbox = _yj_launch
    package.close = package.ui.close
    package.show = package.ui.show
    return package.show()


def onMayaDroppedPythonFile(*args):
    return _yj_launch()


if __name__ == "__main__":
    _yj_launch()
