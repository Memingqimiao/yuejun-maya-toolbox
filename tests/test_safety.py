# -*- coding: utf-8 -*-
"""Offline regression tests; Maya mocks do NOT establish Maya runtime compatibility."""
import ast
import importlib
import ntpath
import os
import shutil
from pathlib import Path
import sys
import subprocess
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch


# This suite must never replace the modules of a live Maya session.
if "maya.cmds" in sys.modules:
    raise RuntimeError("Run this test with regular Python outside Maya.")
maya = types.ModuleType("maya")
maya.cmds = MagicMock(name="maya.cmds")
maya.mel = MagicMock(name="maya.mel")
api = types.ModuleType("maya.api")
api.OpenMaya = MagicMock(name="OpenMaya")
sys.modules.update({"maya": maya, "maya.cmds": maya.cmds, "maya.mel": maya.mel,
                    "maya.api": api, "maya.api.OpenMaya": api.OpenMaya})

from yuejun_toolbox import config, core, ui, project, gn


class GnInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.package = self.root / "Plugins" / "GN_ImportExport_v2.73"
        maya_payload = self.package / "Maya" / "GN_ImportExport"
        (maya_payload / "GN_scripts").mkdir(parents=True)
        (maya_payload / "GN_ImportExport.mel").write_text("// mel", encoding="utf-8")
        (maya_payload / "GN_scripts" / "GN_Import.py").write_text("x = 1", encoding="utf-8")
        zbrush = self.package / "ZBrush" / "GN_ImportExport"
        zbrush.mkdir(parents=True)
        (zbrush / "ZFileUtils64.dll").write_bytes(b"dll")
        (self.package / "ZBrush" / "GN_ImportExport.zsc").write_bytes(b"zsc")
        self.scripts = self.root / "maya" / "2022" / "scripts"
        self.scripts.mkdir(parents=True)
        self.plugs = self.root / "ZBrush" / "ZStartup" / "ZPlugs64"
        self.plugs.mkdir(parents=True)
        for target, kwargs in (("asset_path", {"side_effect": lambda rel: str(self.root / rel)}),
                               ("settings", {"return_value": {}})):
            patcher = patch.object(gn.config, target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)
        for target, kwargs in (("maya_scripts_dir", {"return_value": str(self.scripts)}),
                               ("zbrush_plugin_dirs", {"return_value": [str(self.plugs)]})):
            patcher = patch.object(gn, target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)

    def tearDown(self):
        self.temp.cleanup()

    def test_newest_versioned_package_is_selected(self):
        # GN numbers its builds v2-73, so 73 is a revision of v2, not a decimal.
        (self.root / "Plugins" / "GN_ImportExport_v2.9" / "Maya" / "GN_ImportExport").mkdir(parents=True)
        self.assertEqual(os.path.basename(gn.package_root()), "GN_ImportExport_v2.73")
        (self.root / "Plugins" / "GN_ImportExport_v3.0" / "Maya" / "GN_ImportExport").mkdir(parents=True)
        self.assertEqual(os.path.basename(gn.package_root()), "GN_ImportExport_v3.0")
        self.assertEqual(gn.package_version(gn.package_root()), "3.0")

    def test_missing_package_reports_an_actionable_error(self):
        shutil.rmtree(str(self.package))
        with self.assertRaises(gn.GnError):
            gn.package_root()

    def test_install_copies_both_halves_and_writes_user_setup(self):
        with patch.object(gn, "load", return_value="loaded"):
            result = gn.install()
        self.assertTrue((self.scripts / "GN_ImportExport" / "GN_ImportExport.mel").is_file())
        self.assertTrue((self.scripts / "GN_ImportExport" / "GN_scripts" / "GN_Import.py").is_file())
        self.assertTrue((self.plugs / "GN_ImportExport.zsc").is_file())
        self.assertTrue((self.plugs / "GN_ImportExport" / "ZFileUtils64.dll").is_file())
        setup = (self.scripts / "userSetup.mel").read_text(encoding="utf-8")
        self.assertIn("GN_ImportExport/GN_ImportExport.mel", setup)
        self.assertIn("loaded", result)

    def test_existing_user_setup_is_backed_up_and_kept(self):
        (self.scripts / "userSetup.mel").write_text('print "mine";\n', encoding="utf-8")
        with patch.object(gn, "load", return_value="loaded"):
            gn.install()
        setup = (self.scripts / "userSetup.mel").read_text(encoding="utf-8")
        self.assertIn('print "mine";', setup)
        self.assertIn("GN_ImportExport/GN_ImportExport.mel", setup)
        self.assertEqual((self.scripts / "userSetup.mel.yuejun_backup").read_text(encoding="utf-8"),
                         'print "mine";\n')

    def test_second_install_does_not_duplicate_the_startup_line(self):
        with patch.object(gn, "load", return_value="loaded"):
            gn.install()
            gn.install()
        setup = (self.scripts / "userSetup.mel").read_text(encoding="utf-8")
        self.assertEqual(setup.count("GN_ImportExport/GN_ImportExport.mel"), 1)

    def test_status_reports_missing_pieces_without_changing_disk(self):
        with patch.object(gn, "_commands_available", return_value=False):
            report = gn.status()
        self.assertIn("未安装", report)
        self.assertIn("尚未完全就绪", report)
        self.assertFalse((self.scripts / "GN_ImportExport").exists())
        self.assertFalse((self.scripts / "userSetup.mel").exists())

    def test_gn_tools_are_registered_in_the_gn_group(self):
        keys = [tool.key for title, tools in config.GROUPS if title.startswith("GN") for tool in tools]
        self.assertEqual(keys, ["gn_import", "gn_export", "gn_check", "gn_install"])
        self.assertTrue(core.availability(config.TOOLS["gn_install"])[0])


class CopySafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.target = self.root / "project"
        self.source.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_nested_copy_never_overwrites_existing_files(self):
        (self.source / "sub").mkdir()
        (self.source / "sub" / "new.exr").write_bytes(b"new")
        (self.source / "keep.exr").write_bytes(b"replacement")
        self.target.mkdir()
        (self.target / "keep.exr").write_bytes(b"user original")
        self.assertEqual(core.copy_folder(str(self.source), str(self.target)), (1, 1))
        self.assertEqual((self.target / "keep.exr").read_bytes(), b"user original")
        self.assertEqual((self.target / "sub" / "new.exr").read_bytes(), b"new")
        self.assertEqual(core.copy_folder(str(self.source), str(self.target)), (0, 2))

    def test_incomplete_copy_is_removed(self):
        (self.source / "bad.exr").write_bytes(b"data")
        with patch.object(core.shutil, "copyfileobj", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                core.copy_folder(str(self.source), str(self.target))
        self.assertFalse((self.target / "bad.exr").exists())

    def test_source_inside_destination_and_reverse_are_refused(self):
        for destination in (self.source, self.source / "nested", self.root):
            with self.assertRaises(core.ToolError):
                core.copy_folder(str(self.source), str(destination))

    def test_windows_different_drives_are_not_treated_as_nested(self):
        with patch.object(core.os.path, "commonpath", ntpath.commonpath):
            self.assertFalse(core._inside("D:/project", "C:/resources"))

    def test_missing_source_is_an_error(self):
        with self.assertRaises(core.ToolError):
            core.copy_folder(str(self.root / "missing"), str(self.target))


class UndoSafetyTests(unittest.TestCase):
    def setUp(self):
        self.commands = MagicMock()
        self.queue = ["UserPreviousAction"]
        self.token = None
        self.opened = False
        self.enabled = True

        def undo_info(**kwargs):
            if kwargs.get("openChunk"):
                self.opened = True
                self.token = kwargs["chunkName"]
            elif kwargs.get("closeChunk"):
                self.opened = False
            elif kwargs.get("state"):
                return self.enabled
            elif kwargs.get("undoQueueEmpty"):
                return not self.queue
            elif kwargs.get("undoName"):
                return self.queue[-1]

        self.commands.undoInfo.side_effect = undo_info
        self.commands.undo.side_effect = lambda: self.queue.pop()
        self.patcher = patch.object(core, "cmds", self.commands)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_exception_before_mutation_does_not_undo_user_history(self):
        with self.assertRaises(RuntimeError):
            with core.undo_chunk("failed"):
                raise RuntimeError("failed before mutation")
        self.commands.undo.assert_not_called()
        self.assertEqual(self.queue, ["UserPreviousAction"])
        self.assertFalse(self.opened)

    def test_failed_mutation_rolls_back_only_own_chunk(self):
        with self.assertRaises(RuntimeError):
            with core.undo_chunk("failed"):
                self.queue.append(self.token)
                raise RuntimeError("failed after mutation")
        self.commands.undo.assert_called_once()
        self.assertEqual(self.queue, ["UserPreviousAction"])
        self.assertFalse(self.opened)

    def test_success_keeps_undo_entry_and_closes_chunk(self):
        with core.undo_chunk("success"):
            self.queue.append(self.token)
        self.commands.undo.assert_not_called()
        self.assertFalse(self.opened)

    def test_disabled_undo_refuses_edits(self):
        self.enabled = False
        with self.assertRaises(core.ToolError):
            with core.undo_chunk("disabled"):
                self.fail("must not enter operation")
        self.assertFalse(self.opened)


class SceneSafetyTests(unittest.TestCase):
    def setUp(self):
        # These tests exercise scene dispatch; the project module is integration-tested separately.
        session = MagicMock()
        session.copy_file.side_effect = lambda path, category: path
        for target, kwargs in (("SyncSession", {"return_value": session}),
                               ("localize", {"return_value": ""}),
                               ("require_project", {"return_value": "C:/Project"})):
            patcher = patch.object(project, target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_blend_source_is_marked_without_touching_the_scene(self):
        commands = MagicMock()
        commands.ls.side_effect = lambda *args, **kwargs: (
            ["|NewShape"] if kwargs.get("selection") else ["abc-123"])
        commands.nodeType.return_value = "transform"
        commands.listRelatives.return_value = ["|NewShape|NewShapeShape"]
        with patch.object(core, "cmds", commands), patch.object(
                core, "mesh", return_value=("|NewShape", "|NewShape|NewShapeShape",
                                            MagicMock(numVertices=10, numPolygons=4))):
            result = core.mark_blend_source()
        commands.rename.assert_not_called()
        commands.blendShape.assert_not_called()
        self.assertIn("NewShape", result)
        self.assertEqual(core._BLEND_SOURCE["uuid"], "abc-123")

    def test_blend_requires_exactly_one_selected_mesh_to_mark(self):
        commands = MagicMock()
        commands.ls.return_value = []
        with patch.object(core, "cmds", commands):
            with self.assertRaises(core.ToolError):
                core.mark_blend_source()
        commands.rename.assert_not_called()

    def test_blend_target_refuses_mismatched_topology_before_changing_anything(self):
        commands = MagicMock()
        meshes = {"|Source": MagicMock(numVertices=10, numEdges=20, numPolygons=11),
                  "|Base": MagicMock(numVertices=12, numEdges=24, numPolygons=13)}
        with patch.object(core, "cmds", commands), patch.object(
                core, "_selected_meshes", return_value=["|Source", "|Base"]), patch.object(
                core, "mesh", side_effect=lambda node, editable=False: (node, node, meshes[node])):
            with self.assertRaises(core.ToolError) as error:
                core.blend_target()
        self.assertIn("拓扑", str(error.exception))
        commands.blendShape.assert_not_called()
        commands.delete.assert_not_called()

    def test_blend_target_works_on_any_matching_topology_without_metahuman_names(self):
        commands = MagicMock()
        commands.blendShape.return_value = ["blendShape7"]
        commands.listHistory.return_value = []
        shared = MagicMock(numVertices=10, numEdges=20, numPolygons=11)
        with patch.object(core, "cmds", commands), patch.object(
                core, "_selected_meshes", return_value=["|grp|Custom_New", "|grp|Custom_Base"]), patch.object(
                core, "mesh", side_effect=lambda node, editable=False: (node, node, shared)), patch.object(
                core, "undo_chunk", MagicMock()):
            result = core.blend_target()
        commands.blendShape.assert_called_once_with("|grp|Custom_New", "|grp|Custom_Base", weight=(0, 1.0))
        commands.delete.assert_any_call("|grp|Custom_Base", constructionHistory=True)
        commands.delete.assert_any_call("|grp|Custom_New")
        self.assertIn("Custom_Base", result)

    def test_blend_target_can_keep_the_source_mesh(self):
        commands = MagicMock()
        commands.blendShape.return_value = ["blendShape1"]
        commands.listHistory.return_value = []
        shared = MagicMock(numVertices=8, numEdges=12, numPolygons=6)
        with patch.object(core, "cmds", commands), patch.object(
                core, "_selected_meshes", return_value=["|A", "|B"]), patch.object(
                core, "mesh", side_effect=lambda node, editable=False: (node, node, shared)), patch.object(
                core, "undo_chunk", MagicMock()):
            core.blend_target(delete_source=False)
        commands.delete.assert_called_once_with("|B", constructionHistory=True)

    def test_blend_target_reports_deformers_removed_by_history_cleanup(self):
        commands = MagicMock()
        commands.blendShape.return_value = ["blendShape1"]
        commands.listHistory.return_value = ["skinCluster1", "tweak1"]
        commands.nodeType.side_effect = lambda node: (
            "skinCluster" if node.startswith("skinCluster") else "tweak")
        shared = MagicMock(numVertices=8, numEdges=12, numPolygons=6)
        with patch.object(core, "cmds", commands), patch.object(
                core, "_selected_meshes", return_value=["|A", "|B"]), patch.object(
                core, "mesh", side_effect=lambda node, editable=False: (node, node, shared)), patch.object(
                core, "undo_chunk", MagicMock()):
            result = core.blend_target()
        self.assertIn("skinCluster", result)

    def test_blend_target_refuses_the_same_mesh_twice(self):
        commands = MagicMock()
        shared = MagicMock(numVertices=8, numEdges=12, numPolygons=6)
        with patch.object(core, "cmds", commands), patch.object(
                core, "_selected_meshes", return_value=["|Same"]), patch.object(
                core, "_marked_blend_source", return_value="|Same"), patch.object(
                core, "mesh", side_effect=lambda node, editable=False: (node, node, shared)):
            with self.assertRaises(core.ToolError):
                core.blend_target()
        commands.blendShape.assert_not_called()

    def test_blend_target_without_a_marked_source_is_refused(self):
        commands = MagicMock()
        core._BLEND_SOURCE.update(uuid="", name="")
        with patch.object(core, "cmds", commands), patch.object(
                core, "_selected_meshes", return_value=["|Base"]):
            with self.assertRaises(core.ToolError):
                core.blend_target()
        commands.blendShape.assert_not_called()

    def test_growth_import_keeps_original_file_command(self):
        commands = MagicMock()
        with patch.object(core, "cmds", commands), patch.object(core, "require_file", return_value="C:/Resources/Growth.mb"):
            core.execute("import_growth")
        commands.file.assert_called_once_with("C:/Resources/Growth.mb", i=True, force=True, returnNewNodes=True)
        commands.namespace.assert_not_called()

    def test_original_scripts_are_sourced_without_replacement_algorithm(self):
        commands, mel_commands = MagicMock(), MagicMock()
        path = "C:/Resources/Scripts/Skin_Legacy.mel"
        with patch.object(core, "cmds", commands), patch.object(core, "mel", mel_commands), patch.object(core, "require_file", return_value=path):
            core.run_legacy_mel("Scripts/Skin_Legacy.mel")
        self.assertEqual(mel_commands.eval.call_args[0][0], 'source "{}";'.format(path))
        commands.blendShape.assert_not_called()
        commands.transferAttributes.assert_not_called()

    def test_renderer_missing_prevents_file_import(self):
        commands = MagicMock()
        commands.pluginInfo.side_effect = RuntimeError("not loaded")
        with patch.object(core, "cmds", commands), patch.object(core, "require_file", return_value="C:/Test_Vray.mb"):
            with self.assertRaises(core.ToolError):
                core.import_asset("Test_Vray.mb")
        commands.file.assert_not_called()

    def test_import_is_direct_at_root_and_never_calls_namespace_cleanup(self):
        commands = MagicMock()
        commands.file.return_value = ["newNode"]
        with patch.object(core, "cmds", commands), patch.object(core, "require_file", return_value="C:/Eye_Grp.mb"), patch.object(core, "flatten_namespaces") as flatten, patch.object(core, "root_namespace"), patch.object(core, "undo_chunk"), patch.object(core, "preserve_selection"):
            core.import_asset("Eye_Grp.mb")
        kwargs = commands.file.call_args[1]
        self.assertTrue(kwargs["i"])
        self.assertEqual(kwargs["namespace"], ":")
        self.assertTrue(kwargs["mergeNamespacesOnClash"])
        self.assertFalse(kwargs["executeScriptNodes"])
        self.assertNotIn("open", kwargs)
        flatten.assert_not_called()
        commands.namespace.assert_not_called()

    def test_open_preset_refuses_unsaved_work(self):
        commands = MagicMock()
        commands.file.return_value = True
        with patch.object(core, "cmds", commands), patch.object(core, "require_file", return_value="C:/Preset.mb"), self.assertRaises(core.ToolError):
            core.open_scene_preset("Preset.mb")
        self.assertFalse(any(call.kwargs.get("open") for call in commands.file.call_args_list))

    def test_open_preset_uses_open_not_import_or_namespace(self):
        commands = MagicMock()
        with patch.object(core, "cmds", commands), patch.object(core, "require_file", return_value="C:/Preset.mb"), patch.object(core, "scene_modified", return_value=False):
            core.open_scene_preset("Preset.mb")
        commands.file.assert_called_once_with("C:/Preset.mb", open=True, force=False, executeScriptNodes=False)
        commands.namespace.assert_not_called()

    def test_open_preset_discard_requires_explicit_opt_in(self):
        commands = MagicMock()
        with patch.object(core, "cmds", commands), patch.object(core, "require_file", return_value="C:/Preset.mb"), patch.object(core, "scene_modified", return_value=True):
            core.open_scene_preset("Preset.mb", discard_changes=True)
        commands.file.assert_called_once_with("C:/Preset.mb", open=True, force=True, executeScriptNodes=False)

    def test_ui_cancel_never_opens_or_saves_scene(self):
        commands = MagicMock()
        commands.confirmDialog.return_value = "取消"
        window = ui.ToolboxWindow()
        with patch.object(ui, "cmds", commands), patch.object(core, "require_file"), patch.object(core, "require_renderer"), patch.object(core, "scene_modified", return_value=True), patch.object(core, "open_scene_preset") as opened, patch.object(core, "save_scene") as saved:
            window.open_preset("preset_arnold")
        opened.assert_not_called()
        saved.assert_not_called()

    def test_ui_save_error_does_not_open_scene(self):
        commands = MagicMock()
        commands.confirmDialog.return_value = "保存并打开"
        commands.file.return_value = "C:/UserWork.ma"
        window = ui.ToolboxWindow()
        with patch.object(ui, "cmds", commands), patch.object(core, "require_file"), patch.object(core, "require_renderer"), patch.object(core, "scene_modified", return_value=True), patch.object(core, "open_scene_preset") as opened, patch.object(core, "save_scene", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                window.open_preset("preset_arnold")
        opened.assert_not_called()


    def test_reference_is_rejected_without_unlocking(self):
        commands = MagicMock()
        commands.referenceQuery.return_value = True
        with patch.object(core, "cmds", commands), self.assertRaises(core.ToolError):
            core._editable("|referenced")
        commands.lockNode.assert_not_called()


class NamespaceSafetyTests(unittest.TestCase):
    def commands(self, nodes, existing=(), children=()):
        commands = MagicMock()
        def namespace_info(name, **kwargs):
            if kwargs.get("listOnlyNamespaces"):
                return list(children)
            return list(existing if name == ":" else nodes)
        commands.namespaceInfo.side_effect = namespace_info
        commands.ls.return_value = list(nodes) + list(existing)
        commands.referenceQuery.return_value = False
        commands.lockNode.return_value = [False]
        return commands

    def test_existing_name_conflict_does_not_move_or_rename_anything(self):
        commands = self.commands(["|temp:Light"], ["|Light"])
        with patch.object(core, "cmds", commands), self.assertRaises(core.ToolError):
            core.flatten_namespaces([":temp"])
        commands.namespace.assert_not_called()
        commands.rename.assert_not_called()

    def test_nested_duplicate_names_refused_before_any_move(self):
        commands = self.commands(["|temp:a:Light", "|temp:b:Light"])
        with patch.object(core, "cmds", commands), self.assertRaises(core.ToolError):
            core.flatten_namespaces([":temp"])
        commands.namespace.assert_not_called()

    def test_nested_namespaces_removed_deepest_first_without_force(self):
        commands = self.commands(["|temp:Rig", "|temp:Rig|temp:child:Mesh"], children=[":temp:child"])
        with patch.object(core, "cmds", commands):
            self.assertEqual(core.flatten_namespaces([":temp"]), 2)
        self.assertEqual([call.kwargs for call in commands.namespace.call_args_list], [
            {"moveNamespace": (":temp:child", ":"), "force": False},
            {"removeNamespace": ":temp:child"},
            {"moveNamespace": (":temp", ":"), "force": False},
            {"removeNamespace": ":temp"}])
        commands.rename.assert_not_called()

    def test_referenced_nodes_prevent_cleanup(self):
        commands = self.commands(["temp:ReferencedMesh"])
        commands.referenceQuery.return_value = True
        with patch.object(core, "cmds", commands), self.assertRaises(core.ToolError):
            core.flatten_namespaces([":temp"])
        commands.namespace.assert_not_called()



    def test_scoped_node_lookup_excludes_similar_prefixes_and_uses_no_namespace_flags(self):
        nodes = ["|temp:Rig|temp:child:Mesh", "temp:Shader", "temp1:Other", "Original"]
        commands = MagicMock()
        commands.ls.return_value = nodes
        with patch.object(core, "cmds", commands):
            self.assertEqual(core.namespace_nodes([":temp"]), nodes[:2])
        commands.namespaceInfo.assert_not_called()

    def test_current_namespace_and_relative_mode_restored_on_error(self):
        commands = MagicMock()
        commands.namespaceInfo.return_value = ":ArtistRig"
        commands.namespace.return_value = True
        with patch.object(core, "cmds", commands), self.assertRaises(RuntimeError):
            with core.root_namespace():
                raise RuntimeError("operation failed")
        calls = [call.kwargs for call in commands.namespace.call_args_list]
        self.assertEqual(calls[-2:], [{"setNamespace": ":ArtistRig"}, {"relativeNames": True}])


class LegacyDataTests(unittest.TestCase):
    def test_component_data_maps_to_full_namespaced_path(self):
        plan = core.skin_plan("select -r Skin.f[1:2]; polyEditUV -u 0 -v 1; select -r Skin;", "cut_uv", "|group|ns:Skin")
        self.assertEqual(plan[0], ("select", ["|group|ns:Skin.f[1:2]"], {"replace": True}))
        self.assertEqual(plan[1][2], {"uValue": 0, "vValue": 1})

    def test_non_skin_objects_or_script_expressions_are_rejected(self):
        for source in ("select -r Other;", "select -r `delete Skin`;", "delete Skin;", "python(\"evil\");"):
            with self.subTest(source=source), self.assertRaises(core.ToolError):
                core.skin_plan(source, "cut_uv", "|Skin")

    def test_zb_tool_removed_and_presets_import(self):
        self.assertNotIn("zb_groups", config.TOOLS)
        self.assertNotIn("Skin", [title for title, _ in config.GROUPS])
        self.assertNotIn("mh_restore", config.TOOLS)
        self.assertEqual(config.TOOLS["preset_arnold"].kind, "open")
        self.assertEqual(config.TOOLS["preset_vray"].kind, "open")

    def test_out_of_range_is_rejected_before_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.mel"
            path.write_text("select -r Skin.f[42]; polyEditUV -u 0 -v 1;", encoding="utf-8")
            mesh_fn = MagicMock(numPolygons=4)
            with patch.object(core, "require_file", return_value=str(path)), patch.object(core, "named_mesh", return_value=("|Skin", "shape", mesh_fn)), patch.object(core, "undo_chunk") as chunk:
                with self.assertRaises(core.ToolError):
                    core.run_skin_script(config.Tool("cut_uv", "test", "mel", "Scripts/Skin_qieUV.mel", ""))
                chunk.assert_not_called()


class DefaultProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.library = self.root / "Library"
        self.library.mkdir()
        self.app = self.root / "maya"
        (self.app / "projects").mkdir(parents=True)
        commands = MagicMock()
        commands.internalVar.return_value = str(self.app) + os.sep
        for module, target, kwargs in ((project, "cmds", {"new": commands}),
                                       (project.config, "resource_root",
                                        {"return_value": str(self.library)}),
                                       (project.config, "settings", {"return_value": {}})):
            patcher = patch.object(module, target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)

    def tearDown(self):
        self.temp.cleanup()

    def test_default_project_lives_outside_the_resource_library(self):
        root = project.default_project_root()
        self.assertEqual(os.path.basename(root), "Yuejun_Default")
        self.assertFalse(project.inside(root, str(self.library)))

    def test_configured_location_is_honoured(self):
        target = self.root / "Work" / "Preview"
        with patch.object(project.config, "settings",
                          return_value={"default_project_root": str(target)}):
            self.assertEqual(project.normalize(project.default_project_root()),
                             project.normalize(str(target)))

    def test_configured_location_inside_the_library_is_refused(self):
        with patch.object(project.config, "settings",
                          return_value={"default_project_root": str(self.library / "Projects")}):
            with self.assertRaises(project.ProjectError):
                project.default_project_root()

    def test_the_old_in_library_project_is_still_recognised(self):
        roots = [project.normalize(path) for path in project.managed_roots()]
        self.assertIn(project.normalize(str(self.library / "Projects" / "Default")), roots)


class LibraryLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_tool_paths_use_the_current_folder_names(self):
        for tool in config.TOOLS.values():
            if tool.kind in ("mel", "import", "open", "legacy_import", "legacy_mel"):
                head = tool.path.split("/")[0]
                self.assertIn(head, config.REQUIRED_FOLDERS,
                              "{} 仍使用旧目录名 {}".format(tool.key, tool.path))

    def test_current_folder_is_used_when_present(self):
        (self.root / "NodePresets").mkdir()
        (self.root / "NodePresets" / "Disp.ma").write_text("x", encoding="utf-8")
        self.assertEqual(config.resolve_folder(str(self.root), "NodePresets/Disp.ma"),
                         "NodePresets/Disp.ma")

    def test_legacy_folder_is_used_only_as_a_fallback(self):
        (self.root / "Maya_shader_node" / "Arnold").mkdir(parents=True)
        (self.root / "Maya_shader_node" / "Arnold" / "Base_Arnold.ma").write_text("x", encoding="utf-8")
        self.assertEqual(config.resolve_folder(str(self.root), "RenderPresets/Arnold/Base_Arnold.ma"),
                         "Maya_shader_node/Arnold/Base_Arnold.ma")
        self.assertEqual(config.resolve_folder(str(self.root), "Models/VRay_eye.mb"),
                         "Models/VRay_eye.mb")

    def test_legacy_names_are_rewritten_for_project_layout(self):
        self.assertEqual(config.current_path("Maya_Model/Eye_Arnold/a.ma"), "Models/Eye_Arnold/a.ma")
        self.assertEqual(config.current_path("Maya_shader_node/Arnold/b.ma"), "RenderPresets/Arnold/b.ma")
        self.assertEqual(config.current_path("Models/Eye_Arnold/a.ma"), "Models/Eye_Arnold/a.ma")

    def test_assets_are_grouped_under_one_title(self):
        titles = [title for title, _ in config.GROUPS]
        self.assertIn("素材", titles)
        self.assertNotIn("眼球", titles)
        self.assertNotIn("VFace 素材", titles)
        assets = dict(config.GROUPS)["素材"]
        self.assertEqual([tool.key for tool in assets],
                         ["import_eye", "import_eye_arnold", "vface_browser", "mh_female", "mh_male", "mh_apply", "mh_uv", "mh_seams"])

    def test_vface_path_is_only_offered_by_the_browser(self):
        source = (Path(__file__).resolve().parents[1] / "yuejun_toolbox" / "ui.py").read_text(encoding="utf-8")
        self.assertNotIn("vface_path_field", source)
        self.assertNotIn("choose_vface_root", source)
        browser = (Path(__file__).resolve().parents[1] / "yuejun_toolbox" / "vface_ui.py").read_text(encoding="utf-8")
        self.assertIn("set_vface_root", browser)


class ConfigurationAndUiTests(unittest.TestCase):
    def test_renderer_filters_and_project_button_order(self):
        arnold = {tool.key for _, group in config.visible_groups(False) for tool in group}
        vray = {tool.key for _, group in config.visible_groups(True) for tool in group}
        self.assertFalse(arnold & config.VRAY_TOOLS)
        self.assertFalse(vray & config.ARNOLD_TOOLS)
        self.assertTrue(config.ARNOLD_TOOLS <= arnold)
        self.assertTrue(config.VRAY_TOOLS <= vray)
        self.assertEqual([tool.key for tool in config.PROJECT_GROUP[1]],
                         ["project_window", "set_project", "check_project"])

    def test_pending_original_script_is_cancelled_when_window_is_reloaded(self):
        old_window = ui.ToolboxWindow()
        old_window.busy = True
        with patch.object(ui, "_instance", ui.ToolboxWindow()), patch.object(core, "execute") as execute:
            old_window.run_deferred_legacy("update_growth")
        execute.assert_not_called()
        self.assertFalse(old_window.busy)


    def test_new_launcher_switches_away_from_cached_old_package(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            for version in ("old", "new"):
                package = base / version / "yuejun_toolbox"
                package.mkdir(parents=True)
                (package / "__init__.py").write_text(
                    "__version__ = {!r}\ndef close():\n    pass\ndef reload_toolbox():\n    return __version__\n".format(version), encoding="utf-8")
            launcher = base / "new" / "launch_maya.py"
            launcher.write_bytes((root / "launch_maya.py").read_bytes())
            script = "import sys,runpy; sys.path.insert(0,sys.argv[1]); import yuejun_toolbox; assert yuejun_toolbox.__version__ == 'old'; entry=runpy.run_path(sys.argv[2]); assert entry['launch']() == 'new'"
            result = subprocess.run([sys.executable, "-c", script, str(base / "old"), str(launcher)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_old_default_setting_migrates_once(self):
        values = {config.ROOT_OPTION: config.OLD_DEFAULT_ROOT}
        def option_var(**kwargs):
            if "exists" in kwargs:
                return kwargs["exists"] in values
            if "query" in kwargs:
                return values[kwargs["query"]]
            key, value = kwargs.get("stringValue", kwargs.get("intValue"))
            values[key] = value
        commands = MagicMock()
        commands.optionVar.side_effect = option_var
        with patch.object(config, "cmds", commands):
            config.migrate_preferences()
            self.assertEqual(values[config.ROOT_OPTION], config.DEFAULT_ROOT)
            values[config.ROOT_OPTION] = config.OLD_DEFAULT_ROOT
            config.migrate_preferences()
            self.assertEqual(values[config.ROOT_OPTION], config.OLD_DEFAULT_ROOT)

    def test_custom_resource_setting_is_not_overwritten(self):
        commands = MagicMock()
        commands.optionVar.side_effect = [False, True, "D:/ArtistResources", None]
        with patch.object(config, "cmds", commands):
            config.migrate_preferences()
        self.assertFalse(any("stringValue" in call.kwargs for call in commands.optionVar.call_args_list))

    def test_resource_path_escape_is_refused(self):
        with tempfile.TemporaryDirectory() as root, patch.object(config, "resource_root", return_value=root):
            with self.assertRaises(ValueError):
                config.asset_path("../outside.mel")

    def test_missing_file_has_actionable_disabled_state(self):
        with tempfile.TemporaryDirectory() as root, patch.object(config, "resource_root", return_value=root):
            available, message = core.availability(config.Tool("cut_uv", "test", "mel", "Scripts/Skin_qieUV.mel", ""))
        self.assertFalse(available)
        self.assertIn("Skin_qieUV.mel", message)

    def test_ui_boundary_handles_maya_runtime_error(self):
        window = ui.ToolboxWindow()
        with patch.object(window, "message") as message, patch.object(ui._LOG, "exception"):
            self.assertIsNone(window.guarded(MagicMock(side_effect=RuntimeError("Maya failed"))))
        self.assertTrue(message.call_args[1]["error"])

    def test_reload_closes_ui_before_reloading_modules(self):
        import yuejun_toolbox
        events = []
        with patch.object(ui, "close", side_effect=lambda: events.append("close")), patch.object(ui, "show", side_effect=lambda: events.append("show")), patch.object(importlib, "reload", side_effect=lambda module: events.append(module.__name__)):
            yuejun_toolbox.reload_toolbox()
        self.assertEqual(events, ["close", "yuejun_toolbox.config", "yuejun_toolbox.preview", "yuejun_toolbox.project", "yuejun_toolbox.core", "yuejun_toolbox.eyes", "yuejun_toolbox.gn", "yuejun_toolbox.metahuman", "yuejun_toolbox.vface", "yuejun_toolbox.vface_ui", "yuejun_toolbox.notes_data", "yuejun_toolbox.notes", "yuejun_toolbox.ui", "show"])

    def test_python37_grammar(self):
        if sys.version_info < (3, 8):
            self.skipTest("feature_version argument needs Python 3.8+; use compile on 3.7")
        root = Path(__file__).resolve().parents[1]
        files = list((root / "yuejun_toolbox").glob("*.py")) + [root / "launch_maya.py"]
        for path in files:
            with self.subTest(path=path.name):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 7))


if __name__ == "__main__":
    unittest.main()
