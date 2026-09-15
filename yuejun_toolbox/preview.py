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
