# -*- coding: utf-8 -*-
"""GN Import/Export plugin discovery and installation; no UI creation."""
import os
import re
import shutil

from maya import cmds, mel

from . import config

PLUGIN_FOLDER = "Plugins"
PLUGIN_PREFIX = "GN_ImportExport"
USER_SETUP_LINE = 'evalDeferred("source \\"GN_ImportExport/GN_ImportExport.mel\\"; GN_ImportExport");'
ZBRUSH_OPTION = "zbrush_root"
_VERSION = re.compile(r"(\d+)")


class GnError(RuntimeError):
    """An actionable GN installation error to be displayed by the UI boundary."""


def _version_key(name):
    return [int(part) for part in _VERSION.findall(name)] or [0]


def package_root():
    """Newest Plugins/GN_ImportExport* folder that carries the Maya payload."""
    try:
        folder = config.asset_path(PLUGIN_FOLDER)
    except ValueError as error:
        raise GnError(str(error))
    if not os.path.isdir(folder):
        raise GnError("素材库中没有 {} 目录，请先把 GN 安装包放进去。".format(PLUGIN_FOLDER))
    candidates = [name for name in os.listdir(folder)
                  if name.startswith(PLUGIN_PREFIX) and
                  os.path.isdir(os.path.join(folder, name, "Maya", "GN_ImportExport"))]
    if not candidates:
        raise GnError("在 {} 中找不到 GN 安装包（需要 {}*/Maya/GN_ImportExport）。".format(
            folder, PLUGIN_PREFIX))
    return os.path.join(folder, max(candidates, key=_version_key))


def package_version(root):
    match = _VERSION.findall(os.path.basename(root))
    return ".".join(match) if match else "未知版本"


def maya_scripts_dir():
    """The folder GN_ImportExport.mel resolves its icons against."""
    path = cmds.internalVar(userScriptDir=True)
    if not path:
        raise GnError("无法获取 Maya 用户脚本目录。")
    return os.path.normpath(path)


def zbrush_plugin_dirs():
    """Configured ZPlugs64 folder, otherwise the standard install locations."""
    configured = config.settings().get(ZBRUSH_OPTION, "")
    if configured:
        plugs = os.path.join(configured, "ZStartup", "ZPlugs64")
        return [plugs] if os.path.isdir(plugs) else [configured] if os.path.isdir(configured) else []
    found = []
    for drive in ("C:", "D:", "E:", "F:"):
        for program in ("Program Files", "Program Files (x86)"):
            for vendor in ("Pixologic", "Maxon ZBrush", "Maxon"):
                base = os.path.join(drive + os.sep, program, vendor)
                if not os.path.isdir(base):
                    continue
                for name in sorted(os.listdir(base)):
                    plugs = os.path.join(base, name, "ZStartup", "ZPlugs64")
                    if os.path.isdir(plugs):
                        found.append(plugs)
    return found


def _maya_installed(scripts_dir):
    return os.path.isfile(os.path.join(scripts_dir, "GN_ImportExport", "GN_ImportExport.mel"))


def _user_setup_ready(scripts_dir):
    path = os.path.join(scripts_dir, "userSetup.mel")
    if not os.path.isfile(path):
        return False
    with open(path, "r", encoding="utf-8-sig", errors="replace") as stream:
        return "GN_ImportExport/GN_ImportExport.mel" in stream.read()


def _commands_available():
    try:
        return bool(mel.eval('exists "GN_Import"')) and bool(mel.eval('exists "GN_Export"'))
    except Exception:
        return False


def _zbrush_installed(plugs):
    return (os.path.isfile(os.path.join(plugs, "GN_ImportExport.zsc")) and
            os.path.isdir(os.path.join(plugs, "GN_ImportExport")))


def status():
    """Human readable report; never changes anything on disk."""
    lines = []
    try:
        root = package_root()
        lines.append("安装包：{}（v{}）".format(root, package_version(root)))
    except GnError as error:
        root = None
        lines.append("安装包：未找到。{}".format(error))

    scripts_dir = maya_scripts_dir()
    installed = _maya_installed(scripts_dir)
    lines.append("Maya 脚本目录：{}".format(scripts_dir))
    lines.append("Maya 端 GN 文件：{}".format("已安装" if installed else "未安装"))
    lines.append("userSetup.mel 自启动：{}".format(
        "已配置" if _user_setup_ready(scripts_dir) else "未配置"))
    lines.append("当前会话 GN 命令：{}".format(
        "可用" if _commands_available() else "不可用（安装后需重启 Maya 或点击安装）"))

    plugs = zbrush_plugin_dirs()
    if not plugs:
        lines.append("ZBrush：未找到 ZStartup/ZPlugs64；可在 Settings/toolbox.json 设置 "
                     "zbrush_root 指向 ZBrush 安装目录。")
    for path in plugs:
        lines.append("ZBrush 插件目录：{}（{}）".format(
            path, "已安装 GN" if _zbrush_installed(path) else "未安装 GN"))

    ready = bool(root) and installed and _commands_available() and any(
        _zbrush_installed(path) for path in plugs)
    lines.append("结论：{}".format(
        "GN 已就绪。" if ready else "尚未完全就绪，可点击“安装 GN 插件”。"))
    return "\n".join(lines)


def _copy_tree(source, destination):
    """Recursive copy that overwrites GN's own files; Python 3.7 has no dirs_exist_ok."""
    if not os.path.isdir(source):
        raise GnError("安装包缺少目录：{}".format(source))
    for current, _, files in os.walk(source):
        target_dir = os.path.join(destination, os.path.relpath(current, source))
        os.makedirs(target_dir, exist_ok=True)
        for name in files:
            shutil.copy2(os.path.join(current, name), os.path.join(target_dir, name))


def _write_user_setup(scripts_dir):
    path = os.path.join(scripts_dir, "userSetup.mel")
    existing = ""
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8-sig", errors="replace") as stream:
            existing = stream.read()
        if "GN_ImportExport/GN_ImportExport.mel" in existing:
            return False
        shutil.copy2(path, path + ".yuejun_backup")
    text = existing.rstrip("\n")
    text = (text + "\n\n" if text else "") + USER_SETUP_LINE + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
    return True


def install():
    """Copy the packaged plugin to Maya and ZBrush, then load it in this session."""
    root = package_root()
    scripts_dir = maya_scripts_dir()
    os.makedirs(scripts_dir, exist_ok=True)
    _copy_tree(os.path.join(root, "Maya", "GN_ImportExport"),
               os.path.join(scripts_dir, "GN_ImportExport"))
    report = ["已安装 Maya 端到 {}。".format(scripts_dir)]
    report.append("已写入 userSetup.mel 自启动（原文件已备份）。" if _write_user_setup(scripts_dir)
                  else "userSetup.mel 已有自启动配置，未重复写入。")

    zbrush_source = os.path.join(root, "ZBrush")
    plugs = zbrush_plugin_dirs()
    if not os.path.isdir(zbrush_source):
        report.append("安装包不含 ZBrush 端，已跳过。")
    elif not plugs:
        report.append("未找到 ZBrush 的 ZStartup/ZPlugs64，已跳过；请手动复制 {} 的内容。".format(
            zbrush_source))
    else:
        done = []
        for path in plugs:
            try:
                for name in os.listdir(zbrush_source):
                    source = os.path.join(zbrush_source, name)
                    target = os.path.join(path, name)
                    if os.path.isdir(source):
                        _copy_tree(source, target)
                    else:
                        shutil.copy2(source, target)
                done.append(path)
            except OSError as error:
                report.append("ZBrush 端复制失败（{}）：{}。请以管理员身份重试。".format(path, error))
        if done:
            report.append("已安装 ZBrush 端到 {}。ZBrush 需重启后生效。".format("、".join(done)))

    report.append(load())
    return " ".join(report)


def load():
    """Source the installed MEL and rebuild the GN menu without restarting Maya."""
    scripts_dir = maya_scripts_dir()
    script = os.path.join(scripts_dir, "GN_ImportExport", "GN_ImportExport.mel")
    if not os.path.isfile(script):
        raise GnError("找不到已安装的 GN_ImportExport.mel，请先安装。")
    if scripts_dir not in (os.environ.get("MAYA_SCRIPT_PATH") or ""):
        os.environ["MAYA_SCRIPT_PATH"] = os.pathsep.join(
            part for part in ((os.environ.get("MAYA_SCRIPT_PATH") or ""), scripts_dir) if part)
    try:
        mel.eval('source "{}";'.format(script.replace("\\", "/").replace('"', '\\"')))
        mel.eval("GN_ImportExport;")
    except RuntimeError as error:
        raise GnError("GN 脚本加载失败：{}。请重启 Maya 后再试。".format(error))
    return "GN 菜单已在当前会话载入。"
