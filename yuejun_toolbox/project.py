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
    managed = normalize(root) == normalize(os.path.join(library, "Projects", "Default"))
    if (inside(root, library) or inside(library, root)) and not managed:
        raise ProjectError("工作项目和素材库不能相同或互相包含，请设置独立的项目目录。")
    for rule, fallback in (("scene", "scenes"), ("sourceImages", "sourceimages"),
                           ("images", "images"), ("renderData", "renderData")):
        rule_directory(root, rule, fallback)
    return root


def ensure_project():
    """Use the user's valid project or one reusable, isolated library workspace."""
    try:
        return require_project()
    except ProjectError:
        pass
    library = os.path.realpath(config.resource_root())
    root = os.path.realpath(os.path.join(library, "Projects", "Default"))
    if not inside(root, library) or root == library:
        raise ProjectError("默认项目目录指向素材库之外，请检查 Projects 目录。")
    os.makedirs(root, exist_ok=True)
    workspace = os.path.join(root, "workspace.mel")
    rules = (("scene", "scenes"), ("sourceImages", "sourceimages"), ("images", "images"),
             ("renderData", "renderData"), ("fileCache", "cache/nCache"),
             ("diskCache", "data"), ("sound", "sound"))
    if not os.path.isfile(workspace):
        with open(workspace, "x", encoding="utf-8") as stream:
            stream.write("// Yuejun Toolbox reusable Maya project\n")
            for rule, folder in rules:
                stream.write('workspace -fr "{}" "{}";\n'.format(rule, folder))
    cmds.workspace(root, openWorkspace=True)
    for rule, folder in rules:
        path = rule_directory(root, rule, folder)
        os.makedirs(path, exist_ok=True)
    return require_project()


def digest(path):
    result = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def normalize(path):
    return os.path.normcase(os.path.realpath(path))


def revision_folder(parent, files):
    """Readable revision numbers; reuse a matching revision without overwriting edits."""
    checksums = {os.path.basename(path): digest(path) for path in files}
    for number in range(1, 10000):
        folder = os.path.join(parent, "versions", "Revision_{:03d}".format(number))
        if not os.path.exists(folder):
            return folder
        if all(os.path.isfile(os.path.join(folder, name)) and digest(os.path.join(folder, name)) == checksum
               for name, checksum in checksums.items()):
            return folder
    raise ProjectError("素材版本过多，请整理：" + parent)


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
        self.packages = []

    def register_package(self, source_root, name):
        if not re.fullmatch(r"[A-Za-z0-9_./ -]+", name) or ".." in name.split("/"):
            raise ProjectError("扩展包名称不合法：" + name)
        self.packages.append((os.path.realpath(source_root), name))

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
        package = next(((root, name) for root, name in self.packages if inside(source, root)), None)
        if package:
            relative = os.path.join(package[1], os.path.relpath(source, package[0]))
        elif inside(source, self.library):
            relative = config.modern_path(os.path.relpath(source, self.library)).replace("/", os.sep)
            # Keep one recognizable Arnold directory under each Maya file rule.
            arnold = os.path.join("RenderPresets", "Arnold") + os.sep
            if relative.startswith(arnold):
                tail = relative[len(arnold):]
                for prefix in ("sourceimages" + os.sep, "renderData" + os.sep):
                    if tail.startswith(prefix):
                        tail = tail[len(prefix):]
                relative = os.path.join("Arnold", tail)
        else:
            # Preserve a readable source hierarchy, including drive/server identity.
            readable = re.sub(r"[:<>\"|?*]", "_", os.path.abspath(source)).lstrip("/\\")
            relative = os.path.join("External", readable)
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
            legacy_hash = re.search(r"(?:^|/)External/[0-9a-f]{12}/", previous["target"].replace("\\", "/"))
            if os.path.isfile(recorded) and not legacy_hash:
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
                target = os.path.join(revision_folder(os.path.dirname(base), [source]), os.path.basename(base))
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
        for marker in ("Maya_Texture", "Maya_Light", "Maya_Model", "Maya_shader_node",
                       "Textures", "Lights", "Models", "RenderPresets", "NodePresets"):
            match = re.search(r"(?:^|/)" + marker + r"/(.*)$", raw, re.I)
            if match:
                candidates.insert(0, os.path.join(self.library, config.modern_path(marker + "/" + match.group(1))))
        for path in candidates:
            if pattern_files(path):
                return os.path.normpath(path)
        # Old supplied files can carry the author's obsolete absolute drive paths.
        if self._basenames is None:
            self._basenames = {}
            for folder, dirs, files in os.walk(self.library, followlinks=False):
                dirs[:] = [name for name in dirs if name not in ("_Backups", ".mayaSwatches", "Projects", "Settings") and
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
                folder = revision_folder(os.path.dirname(self.destination(source, category)), files)
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
