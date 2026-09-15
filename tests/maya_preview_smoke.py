# -*- coding: utf-8 -*-
"""Verify preview files and real Maya save cancellation in an isolated process."""
import importlib
import os
import sys
import tempfile
from unittest.mock import patch
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    import maya.standalone
    maya.standalone.initialize(name="python")
    from maya import cmds
    from yuejun_toolbox import config, core, preview, project
    root = tempfile.mkdtemp(prefix="YuejunPreviewTest_")
    library = os.path.join(root, "library")
    os.makedirs(library)
    source = os.path.join(library, "Fixture.ma")
    texture = os.path.join(library, "fixture.png")
    with open(texture, "wb") as stream:
        stream.write(b"texture fixture")
    try:
        node = cmds.shadingNode("file", asTexture=True, name="TestTexture")
        cmds.setAttr(node + ".fileTextureName", texture.replace("\\", "/"), type="string")
        cmds.file(rename=source)
        cmds.file(save=True, type="mayaAscii")
        original_hash = project.digest(source)
        cmds.file(new=True, force=True)
        unset = os.path.join(root, "unset")
        os.makedirs(unset)
        cmds.workspace(unset, newWorkspace=True)
        with patch.object(config, "resource_root", return_value=library):
            core.open_scene_preset("Fixture.ma")
            assert preview.STATE.active
            assert project.inside(cmds.file(query=True, sceneName=True), preview.STATE.root)
            path = cmds.getAttr("TestTexture.fileTextureName")
            assert os.path.isfile(path) and project.inside(path, preview.STATE.root), path
            for _ in range(2):
                importlib.reload(preview)
                try:
                    cmds.file(save=True, type="mayaAscii")
                except RuntimeError:
                    pass
                else:
                    raise AssertionError("Preview save was not cancelled")
                assert preview.STATE.active
            valid = os.path.join(root, "project")
            os.makedirs(valid)
            cmds.workspace(valid, newWorkspace=True)
            for key, value in (("scene", "scenes"), ("sourceImages", "textures"), ("images", "images"), ("renderData", "renderData")):
                cmds.workspace(fileRule=(key, value))
            cmds.workspace(saveWorkspace=True)
            cmds.workspace(valid, openWorkspace=True)
            # Even after setting a project, preview must never overwrite a library file.
            cmds.file(rename=source)
            try:
                cmds.file(save=True, type="mayaAscii")
            except RuntimeError:
                pass
            else:
                raise AssertionError("Preview saved over library source")
            assert project.digest(source) == original_hash
            target = os.path.join(valid, "scenes", "Saved.ma")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            cmds.file(rename=target)
            cmds.file(save=True, type="mayaAscii")
            assert os.path.isfile(target)
            assert not preview.STATE.active
            assert project.inside(cmds.getAttr("TestTexture.fileTextureName"), os.path.join(valid, "textures"))
            assert project.digest(source) == original_hash
            cmds.file(new=True, force=True)
            cmds.workspace(unset, openWorkspace=True)
            core.import_asset("Fixture.ma")
            assert preview.STATE.active
            cmds.file(new=True, force=True)
            assert not preview.STATE.active
        print("PASS: no-project open/import, save cancellation, reload persistence, source protection, project promotion and new-scene reset")
    finally:
        maya.standalone.uninitialize()


if __name__ == "__main__":
    main()
