# -*- coding: utf-8 -*-
"""Actual eye variant import, selection, undo and reopen checks in isolated Maya."""
import json
import os
import sys
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    import maya.standalone
    maya.standalone.initialize(name="python")
    from maya import cmds
    from yuejun_toolbox import config, project, eyes
    root = tempfile.mkdtemp(prefix="YuejunEye360_")
    report = {"project": root}
    try:
        config.resource_root = lambda: "C:/Yuejun_ToolBox"
        cmds.workspace(root, newWorkspace=True)
        for key, value in (("scene", "scenes"), ("sourceImages", "sourceimages"), ("images", "images"), ("renderData", "renderData")):
            cmds.workspace(fileRule=(key, value))
            os.makedirs(os.path.join(root, value), exist_ok=True)
        cmds.workspace(saveWorkspace=True)
        cmds.workspace(root, openWorkspace=True)
        cmds.loadPlugin("mtoa", quiet=True)
        cmds.loadPlugin("vrayformaya", quiet=True)
        report["import"] = eyes.import_eye("Green", "1k")
        files = cmds.ls(type="file")
        before = {node: cmds.getAttr(node + ".fileTextureName") for node in files}
        assert len(files) == 18
        for path in before.values():
            assert os.path.isfile(path if os.path.isabs(path) else os.path.join(root, path)), path
            assert "_1k." in path, path
            if "Iris_Albedo" in path:
                assert "greenIris" in path, path
        cmds.select("eyes_grp")
        selected = eyes.selected_files()
        report["selected_file_count"] = len(selected)
        assert set(files) <= set(selected), selected
        report["modify"] = eyes.apply("Blue", "4k")
        for node in files:
            path = cmds.getAttr(node + ".fileTextureName")
            assert "_4k." in path, path
            if "Iris_Albedo" in path:
                assert "blueIris" in path, path
        cmds.undo()
        assert all(cmds.getAttr(node + ".fileTextureName") == path for node, path in before.items())
        report["undo"] = True
        report["restore"] = eyes.apply("Original", "512")
        original_paths = [cmds.getAttr(node + ".fileTextureName") for node in files]
        assert all("_512." in path for path in original_paths)
        assert any("blueIris_Albedo" in path for path in original_paths)
        assert any("greenIris_Albedo" in path for path in original_paths)
        scene = os.path.join(root, "scenes", "EditableEyes.mb")
        cmds.file(rename=scene)
        cmds.file(save=True, type="mayaBinary")
        cmds.file(new=True, force=True)
        cmds.file(scene, open=True, force=True, executeScriptNodes=False)
        cmds.select("blueEye_grp")
        report["single_group_files"] = sorted(eyes.selected_files())
        report["after_reopen"] = eyes.apply("Hazel", "2k")
        report["success"] = True
    finally:
        with open("dist/eye_360_validation.json", "w", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
        maya.standalone.uninitialize()
    return 0 if report.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
