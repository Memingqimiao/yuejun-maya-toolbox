# -*- coding: utf-8 -*-
"""Disposable Maya integration. Args: toolbox_root vface_root unset_workspace.

Creates/reuses the requested library's Projects/Default and a review scene there.
Never run in a user's working Maya session.
"""
import os
import sys
import maya.standalone
maya.standalone.initialize(name="python")
from maya import cmds
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from yuejun_toolbox import config, core, project, vface


def main():
    library, extension, unset = map(os.path.abspath, sys.argv[1:4])
    cmds.loadPlugin("mtoa", quiet=True)
    cmds.optionVar(stringValue=(config.ROOT_OPTION, library))
    os.makedirs(unset, exist_ok=True)
    cmds.workspace(unset, openWorkspace=True)
    original = config.asset_path(config.TOOLS["preset_arnold"].path)
    checksum = project.digest(original)
    print(core.open_scene_preset(config.TOOLS["preset_arnold"].path, discard_changes=True))
    expected = os.path.join(library, "Projects", "Default")
    assert project.normalize(project.require_project()) == project.normalize(expected)
    workspace = os.path.join(expected, "workspace.mel")
    stamp = os.stat(workspace).st_mtime_ns
    print(core.open_scene_preset(config.TOOLS["preset_arnold"].path, discard_changes=True))
    assert os.stat(workspace).st_mtime_ns == stamp
    # Also exercise direct VFace switching after the user unsets the project.
    cmds.workspace(unset, openWorkspace=True)
    print(vface.apply(os.path.join(extension, "061")))
    assert project.normalize(project.require_project()) == project.normalize(expected)
    assert os.stat(workspace).st_mtime_ns == stamp
    mesh_count = len(cmds.ls(type="mesh"))
    print(vface.apply(os.path.join(extension, "061")))
    assert len(cmds.ls(type="mesh")) == mesh_count
    paths, errors = project.dependencies()
    outside = []
    for plug, (raw, category) in paths.items():
        path = raw if os.path.isabs(raw) else os.path.join(expected, raw)
        if not project.inside(path, expected):
            outside.append((plug, path))
    assert not outside, outside
    assert project.digest(original) == checksum
    for node in cmds.ls(type="unknown") or []:
        if cmds.unknownNode(node, query=True, realClassName=True) == "nodeGraphEditorInfo":
            cmds.lockNode(node, lock=False)
            cmds.delete(node)
    cmds.file(rename=os.path.join(expected, "scenes", "VFace_061_Review.ma"))
    cmds.file(save=True, type="mayaAscii")
    print("DEFAULT_PROJECT_INTEGRATION_PASS", expected)


try:
    main()
finally:
    maya.standalone.uninitialize()
