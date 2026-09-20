# -*- coding: utf-8 -*-
"""Run ONLY with Maya 2022 mayapy as a separate process, never in a user's scene.

    mayapy tests/maya_smoke.py

This creates disposable geometry and verifies actual undo/history behavior.
UI and renderer/asset checks still need an interactive Maya session.
"""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    import maya.standalone
    maya.standalone.initialize(name="python")
    from maya import cmds
    from maya.api import OpenMaya as om
    from yuejun_toolbox import config, core

    class MayaSafetySmoke(unittest.TestCase):
        def setUp(self):
            cmds.file(new=True, force=True)
            cmds.undoInfo(state=True)
            self.project_temp = tempfile.TemporaryDirectory()
            cmds.workspace(self.project_temp.name, newWorkspace=True)
            for key, value in (("scene", "scenes"), ("sourceImages", "sourceimages"), ("images", "images"), ("renderData", "renderData")):
                cmds.workspace(fileRule=(key, value))
            cmds.workspace(saveWorkspace=True)
            cmds.workspace(self.project_temp.name, openWorkspace=True)

        def tearDown(self):
            cmds.file(new=True, force=True)
            cmds.workspace(os.environ["MAYA_APP_DIR"], openWorkspace=True)
            self.project_temp.cleanup()

        def test_bs_transfers_shape_between_any_meshes_with_matching_topology(self):
            # Deliberately non-MetaHuman names: the old MEL required Skin and Mubiao.
            base = cmds.polyCube(name="Prop_Base")[0]
            source = cmds.polyCube(name="Prop_New")[0]
            cmds.move(0, 2, 0, source + ".vtx[0:7]", relative=True)
            expected = cmds.xform(source + ".vtx[0]", query=True, worldSpace=True, translation=True)
            cmds.select([source, base], replace=True)
            core.execute("blend_target")
            self.assertTrue(cmds.objExists(base))
            self.assertFalse(cmds.objExists(source))
            self.assertFalse(cmds.ls(type="blendShape"))
            moved = cmds.xform(base + ".vtx[0]", query=True, worldSpace=True, translation=True)
            for actual, wanted in zip(moved, expected):
                self.assertAlmostEqual(actual, wanted, places=4)
            cmds.undo()
            self.assertTrue(cmds.objExists(source))

        def test_bs_marks_source_first_and_keeps_it_when_requested(self):
            base = cmds.polyCube(name="Prop_Base")[0]
            source = cmds.polyCube(name="Prop_New")[0]
            cmds.move(0, 1, 0, source + ".vtx[0:7]", relative=True)
            cmds.select(source, replace=True)
            core.execute("rename_target")
            self.assertTrue(cmds.objExists(source))
            cmds.select(base, replace=True)
            core.execute("blend_target", delete_source=False)
            self.assertTrue(cmds.objExists(source))
            self.assertFalse(cmds.ls(type="blendShape"))

        def test_bs_refuses_different_topology_without_changing_the_scene(self):
            base = cmds.polyCube(name="Prop_Base")[0]
            source = cmds.polySphere(name="Prop_New")[0]
            cmds.select([source, base], replace=True)
            with self.assertRaises(core.ToolError):
                core.execute("blend_target")
            self.assertFalse(cmds.ls(type="blendShape"))
            self.assertTrue(cmds.objExists(source))

        def test_original_growth_file_command_imports_without_added_prefix(self):
            with tempfile.TemporaryDirectory() as folder:
                model_folder = os.path.join(folder, "Models")
                os.makedirs(model_folder)
                asset = os.path.join(model_folder, "Skin_shengzhangti.mb")
                cmds.polyPlane(name="Hair_Grtuv")
                cmds.file(asset, exportSelected=True, type="mayaBinary")
                cmds.file(new=True, force=True)
                cmds.polyCube(name="UserSceneSentinel", constructionHistory=False)
                with patch.object(config, "resource_root", return_value=folder):
                    core.execute("import_growth")
                self.assertTrue(cmds.objExists("Hair_Grtuv"))
                self.assertTrue(cmds.objExists("UserSceneSentinel"))
                self.assertFalse(any("Yuejun" in name for name in
                                     (cmds.namespaceInfo(":", listOnlyNamespaces=True, recurse=True) or [])))

        def test_failed_owned_operation_preserves_previous_user_action(self):
            cmds.polyCube(name="UserModel")
            with self.assertRaises(RuntimeError):
                with core.undo_chunk("smoke_failure"):
                    cmds.polyCube(name="TemporaryFailedModel")
                    raise RuntimeError("deliberate regression test failure")
            self.assertFalse(cmds.objExists("TemporaryFailedModel"))
            self.assertTrue(cmds.objExists("UserModel"))

        def test_growth_update_uses_selected_source_and_preserves_history(self):
            resource_root = os.environ.get("YUEJUN_TEST_ASSET_ROOT", "C:/Yuejun_ToolBox")
            if not os.path.isfile(os.path.join(resource_root, "Scripts/Skin_chuangjianshengzhangti.Mel")):
                self.skipTest("Original update script unavailable")
            source = cmds.polyPlane(name="ArbitraryHead")[0]
            cmds.polyMoveVertex(source + ".vtx[*]", translateY=2, constructionHistory=True)
            names = ("Hair_Grtuv", "Brow_Grtuv", "Lash_Grtuv", "Beard_Grtuv")
            for name in names:
                cmds.polyPlane(name=name)
                for uv_set in ("Skin", "Hair"):
                    cmds.polyUVSet(name, copy=True, uvSet="map1", newUVSet=uv_set)
            cmds.select(source)
            source_history = cmds.listHistory(source)
            cmds.softSelect(softSelectEnabled=True)
            with patch.object(config, "resource_root", return_value=resource_root):
                messages = []
                callback = om.MCommandMessage.addCommandOutputCallback(lambda message, kind, *args: messages.append(message))
                try:
                    core.execute("update_growth")
                    core.execute("update_growth")
                finally:
                    om.MMessage.removeCallback(callback)
                self.assertFalse(any("$selection" in message for message in messages), messages)
            self.assertTrue(cmds.objExists(source))
            self.assertEqual(cmds.listHistory(source), source_history)
            self.assertEqual(cmds.ls(selection=True), [source])
            self.assertTrue(cmds.softSelect(query=True, softSelectEnabled=True))
            self.assertFalse(cmds.ls(type="transferAttributes"))
            for name in names:
                self.assertTrue(cmds.objExists(name))
                self.assertEqual(cmds.polyUVSet(name, query=True, currentUVSet=True), ["Hair"])
                self.assertAlmostEqual(cmds.xform(name + ".vtx[0]", query=True, worldSpace=True, translation=True)[1], 2.0, places=4)
            cmds.undo()
            cmds.undo()
            self.assertAlmostEqual(cmds.xform(names[0] + ".vtx[0]", query=True, worldSpace=True, translation=True)[1], 0.0, places=4)
            cmds.softSelect(softSelectEnabled=False)

        def test_direct_import_and_native_repeat_have_no_prefix(self):
            with tempfile.TemporaryDirectory() as folder:
                asset = os.path.join(folder, "Original.ma")
                cmds.polyCube(name="OriginalMesh", constructionHistory=False)
                cmds.file(asset, exportSelected=True, type="mayaAscii", executeScriptNodes=False)
                cmds.file(new=True, force=True)
                cmds.polyCube(name="UserMesh", constructionHistory=False)
                with patch.object(config, "resource_root", return_value=folder):
                    core.import_asset("Original.ma")
                    self.assertTrue(cmds.objExists("OriginalMesh"))
                    self.assertTrue(cmds.objExists("OriginalMeshShape"))
                    core.import_asset("Original.ma")
                    self.assertEqual(len(cmds.ls("OriginalMesh*", type="transform") or []), 2)
                self.assertTrue(cmds.objExists("UserMesh"))
                self.assertEqual(len(cmds.ls("OriginalMesh*", type="transform") or []), 2)
                namespaces = cmds.namespaceInfo(":", listOnlyNamespaces=True, recurse=True) or []
                self.assertFalse(any("_YuejunImport_" in name for name in namespaces))



        def test_open_preset_protects_dirty_scene_then_replaces_saved_scene(self):
            with tempfile.TemporaryDirectory() as folder:
                preset = os.path.join(folder, "Preset.ma")
                saved_work = os.path.join(folder, "UserWork.ma")
                cmds.polyCube(name="PresetMesh", constructionHistory=False)
                core.save_scene(preset)
                cmds.file(new=True, force=True)
                cmds.polyCube(name="UserSceneSentinel", constructionHistory=False)
                original_ids = set(cmds.ls(uuid=True))
                with patch.object(config, "resource_root", return_value=folder):
                    with self.assertRaises(core.ToolError):
                        core.open_scene_preset("Preset.ma")
                    self.assertEqual(set(cmds.ls(uuid=True)), original_ids)
                    core.save_scene(saved_work)
                    core.open_scene_preset("Preset.ma")
                self.assertTrue(cmds.objExists("PresetMesh"))
                self.assertFalse(cmds.objExists("UserSceneSentinel"))
                self.assertTrue(os.path.normpath(cmds.file(query=True, sceneName=True)).startswith(self.project_temp.name))
                namespaces = cmds.namespaceInfo(":", listOnlyNamespaces=True, recurse=True) or []
                self.assertFalse(any("Yuejun" in name for name in namespaces))
                cmds.file(saved_work, open=True, force=True, executeScriptNodes=False)
                self.assertTrue(cmds.objExists("UserSceneSentinel"))

    try:
        print("Maya runtime:", cmds.about(version=True), "Python:", sys.version)
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(MayaSafetySmoke))
        return 0 if result.wasSuccessful() else 1
    finally:
        maya.standalone.uninitialize()


if __name__ == "__main__":
    sys.exit(main())
