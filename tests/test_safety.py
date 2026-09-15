# -*- coding: utf-8 -*-
"""Offline regression tests; Maya mocks do NOT establish Maya runtime compatibility."""
import ast
import importlib
import ntpath
import os
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

from yuejun_toolbox import config, core, ui, project


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

    def test_original_rename_uses_first_selection_and_reports_actual_name(self):
        commands = MagicMock()
        commands.ls.return_value = ["First", "Second"]
        commands.rename.return_value = "Mubiao1"
        with patch.object(core, "cmds", commands):
            result = core.rename_target()
        commands.rename.assert_called_once_with("First", "Mubiao")
        self.assertIn("Mubiao1", result)

    def test_original_rename_with_no_selection_is_noop(self):
        commands = MagicMock()
        commands.ls.return_value = []
        with patch.object(core, "cmds", commands):
            self.assertEqual(core.rename_target(), "No objects selected.")
        commands.rename.assert_not_called()

    def test_growth_import_keeps_original_file_command(self):
        commands = MagicMock()
        with patch.object(core, "cmds", commands), patch.object(core, "require_file", return_value="C:/Resources/Growth.mb"):
            core.execute("import_growth")
        commands.file.assert_called_once_with("C:/Resources/Growth.mb", i=True, force=True, returnNewNodes=True)
        commands.namespace.assert_not_called()

    def test_original_scripts_are_sourced_without_replacement_algorithm(self):
        commands, mel_commands = MagicMock(), MagicMock()
        for key in ("blend_target",):
            path = "C:/Resources/" + config.TOOLS[key].path
            with patch.object(core, "cmds", commands), patch.object(core, "mel", mel_commands), patch.object(core, "require_file", return_value=path):
                core.execute(key)
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
        self.assertEqual(config.TOOLS["preset_arnold"].kind, "open")
        self.assertEqual(config.TOOLS["preset_vray"].kind, "open")

    def test_out_of_range_is_rejected_before_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.mel"
            path.write_text("select -r Skin.f[42]; polyEditUV -u 0 -v 1;", encoding="utf-8")
            mesh_fn = MagicMock(numPolygons=4)
            with patch.object(core, "require_file", return_value=str(path)), patch.object(core, "named_mesh", return_value=("|Skin", "shape", mesh_fn)), patch.object(core, "undo_chunk") as chunk:
                with self.assertRaises(core.ToolError):
                    core.run_skin_script(config.TOOLS["cut_uv"])
                chunk.assert_not_called()


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
            old_window.run_deferred_legacy("blend_target")
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
            available, message = core.availability(config.TOOLS["cut_uv"])
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
        self.assertEqual(events, ["close", "yuejun_toolbox.config", "yuejun_toolbox.preview", "yuejun_toolbox.project", "yuejun_toolbox.core", "yuejun_toolbox.eyes", "yuejun_toolbox.notes_data", "yuejun_toolbox.notes", "yuejun_toolbox.ui", "show"])

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
