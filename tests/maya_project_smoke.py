# -*- coding: utf-8 -*-
"""Project sync integration tests on disposable files and Maya scenes only."""
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
    from yuejun_toolbox import config, core, project

    class ProjectTests(unittest.TestCase):
        def setUp(self):
            cmds.file(new=True, force=True)
            self.temp = tempfile.TemporaryDirectory()
            self.root = os.path.join(self.temp.name, "project")
            self.library = os.path.join(self.temp.name, "library")
            os.makedirs(self.root)
            os.makedirs(self.library)
            cmds.workspace(self.root, newWorkspace=True)
            for key, value in (("scene", "scenes"), ("sourceImages", "sourceimages"),
                               ("images", "images"), ("renderData", "renderData"), ("fileCache", "cache/nCache")):
                cmds.workspace(fileRule=(key, value))
                os.makedirs(os.path.join(self.root, value), exist_ok=True)
            cmds.workspace(saveWorkspace=True)
            cmds.workspace(self.root, openWorkspace=True)
            self.pref = patch.object(config, "resource_root", return_value=self.library)
            self.pref.start()

        def tearDown(self):
            cmds.file(new=True, force=True)
            cmds.workspace(os.environ["MAYA_APP_DIR"], openWorkspace=True)
            self.pref.stop()
            self.temp.cleanup()

        def texture(self, name="test.exr"):
            path = os.path.join(self.library, name)
            with open(path, "wb") as stream:
                stream.write(b"disposable texture fixture")
            return path

        def test_repeat_sync_does_not_write_again_and_preserves_project_edits(self):
            source = self.texture()
            first = project.SyncSession()
            target = first.copy_file(source)
            before = os.stat(target).st_mtime_ns
            again = project.SyncSession()
            self.assertEqual(again.copy_file(source), target)
            self.assertEqual(os.stat(target).st_mtime_ns, before)
            self.assertEqual(again.copied, 0)
            with open(target, "wb") as stream:
                stream.write(b"artist edits")
            project.SyncSession().copy_file(source)
            with open(target, "rb") as stream:
                self.assertEqual(stream.read(), b"artist edits")

        def test_changed_source_updates_an_untouched_project_copy(self):
            source = self.texture()
            target = project.SyncSession().copy_file(source)
            with open(source, "wb") as stream:
                stream.write(b"new source different")
            updated = project.SyncSession().copy_file(source)
            self.assertEqual(updated, target)
            with open(target, "rb") as stream:
                self.assertEqual(stream.read(), b"new source different")
            timestamp = os.stat(target).st_mtime_ns
            project.SyncSession().copy_file(source)
            self.assertEqual(os.stat(target).st_mtime_ns, timestamp)

        def test_changed_source_preserves_artist_copy_and_reuses_revision(self):
            source = self.texture()
            target = project.SyncSession().copy_file(source, "scene")
            with open(target, "wb") as stream:
                stream.write(b"artist version")
            with open(source, "wb") as stream:
                stream.write(b"new library version")
            updated = project.SyncSession().copy_file(source, "scene")
            self.assertNotEqual(updated, target)
            with open(target, "rb") as stream:
                self.assertEqual(stream.read(), b"artist version")
            with open(updated, "rb") as stream:
                self.assertEqual(stream.read(), b"new library version")
            self.assertEqual(project.SyncSession().copy_file(source, "scene"), updated)

        def test_untracked_collision_uses_new_revision(self):
            source = self.texture()
            session = project.SyncSession()
            target = session.destination(source)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as stream:
                stream.write(b"untracked artist file")
            updated = session.resource(source)
            self.assertNotEqual(os.path.join(self.root, updated).replace("/", os.sep), target)
            with open(target, "rb") as stream:
                self.assertEqual(stream.read(), b"untracked artist file")
            self.assertTrue(os.path.isfile(os.path.join(self.root, updated)))

        def test_same_base_ma_mb_selects_newer_format(self):
            import time
            mb = os.path.join(self.library, "Eye.mb")
            ma = os.path.join(self.library, "Eye.ma")
            for path in (mb, ma):
                with open(path, "wb") as stream:
                    stream.write(b"fixture")
            os.utime(mb, (10, 10))
            os.utime(ma, (20, 20))
            self.assertEqual(config.asset_path("Eye.mb"), ma)

        def test_workspace_rule_outside_project_is_rejected(self):
            cmds.workspace(fileRule=("sourceImages", self.library))
            with self.assertRaises(project.ProjectError):
                project.require_project()

        def test_file_texture_import_copies_and_remaps_only_new_nodes(self):
            source = self.texture()
            texture = cmds.shadingNode("file", asTexture=True, name="ImportedTexture")
            cmds.setAttr(texture + ".fileTextureName", source.replace("\\", "/"), type="string")
            asset = os.path.join(self.library, "Texture.ma")
            cmds.select(texture)
            cmds.file(asset, exportSelected=True, type="mayaAscii")
            cmds.file(new=True, force=True)
            existing = cmds.shadingNode("file", asTexture=True, name="ArtistTexture")
            cmds.setAttr(existing + ".fileTextureName", source.replace("\\", "/"), type="string")
            core.import_asset("Texture.ma")
            raw = cmds.getAttr("ImportedTexture.fileTextureName")
            self.assertTrue(project.inside(os.path.join(self.root, raw), self.root), raw)
            self.assertTrue(os.path.isfile(os.path.join(self.root, raw)))
            self.assertEqual(cmds.getAttr(existing + ".fileTextureName"), source.replace("\\", "/"))
            audit = project.audit()
            self.assertIn("ArtistTexture", audit)

        def test_open_preset_uses_project_scene_and_keeps_workspace(self):
            source = self.texture()
            texture = cmds.shadingNode("file", asTexture=True, name="PresetTexture")
            cmds.setAttr(texture + ".fileTextureName", source.replace("\\", "/"), type="string")
            asset = os.path.join(self.library, "Preset.ma")
            cmds.file(rename=asset)
            cmds.file(save=True, type="mayaAscii")
            cmds.file(new=True, force=True)
            core.open_scene_preset("Preset.ma")
            self.assertTrue(project.inside(cmds.file(query=True, sceneName=True), self.root))
            self.assertEqual(project.root_directory(), os.path.realpath(self.root))
            raw = cmds.getAttr("PresetTexture.fileTextureName")
            self.assertTrue(os.path.isfile(os.path.join(self.root, raw)))
            self.assertNotIn("项目外资源", project.audit())

        def test_udim_and_tx_are_copied_as_one_pattern(self):
            for name in ("skin.1001.exr", "skin.1002.exr", "skin.1001.tx"):
                self.texture(name)
            session = project.SyncSession()
            result = session.resource(os.path.join(self.library, "skin.<UDIM>.exr"))
            self.assertEqual(len(project.pattern_files(os.path.join(self.root, result))), 2)
            self.assertEqual(session.copied, 3)

        def test_udim_conflict_keeps_tiles_together_and_is_repeatable(self):
            first = self.texture("skin.1001.exr")
            self.texture("skin.1002.exr")
            raw = os.path.join(self.library, "skin.<UDIM>.exr")
            original = project.SyncSession().resource(raw)
            first_target = os.path.join(self.root, original.replace("<UDIM>", "1001"))
            with open(first_target, "wb") as stream:
                stream.write(b"artist tile")
            with open(first, "wb") as stream:
                stream.write(b"new library tile")
            updated = project.SyncSession().resource(raw)
            self.assertNotEqual(original, updated)
            self.assertEqual(len(project.pattern_files(os.path.join(self.root, updated))), 2)
            self.assertEqual(project.SyncSession().resource(raw), updated)
            with open(first_target, "rb") as stream:
                self.assertEqual(stream.read(), b"artist tile")

        def test_reference_and_internal_texture_are_localized(self):
            source = self.texture()
            texture = cmds.shadingNode("file", asTexture=True, name="ReferenceTexture")
            cmds.setAttr(texture + ".fileTextureName", source.replace("\\", "/"), type="string")
            reference_scene = os.path.join(self.library, "Reference.ma")
            cmds.file(rename=reference_scene)
            cmds.file(save=True, type="mayaAscii")
            cmds.file(new=True, force=True)
            cmds.file(reference_scene, reference=True, namespace="ref")
            session = project.SyncSession(reference_scene)
            project.localize(session)
            self.assertFalse(session.issues, session.issues)
            for ref in cmds.file(query=True, reference=True) or []:
                self.assertTrue(project.inside(ref, self.root), ref)
            raw = cmds.getAttr("ref:ReferenceTexture.fileTextureName")
            self.assertTrue(project.inside(os.path.join(self.root, raw), self.root), raw)

        def test_audit_detects_missing_file_and_external_rule(self):
            node = cmds.shadingNode("file", asTexture=True)
            cmds.setAttr(node + ".fileTextureName", os.path.join(self.library, "missing.exr").replace("\\", "/"), type="string")
            cmds.workspace(fileRule=("images", self.library))
            report = project.audit()
            self.assertIn("缺失资源", report)
            self.assertIn("项目外资源", report)
            self.assertIn("images", report)

    try:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ProjectTests))
        return 0 if result.wasSuccessful() else 1
    finally:
        maya.standalone.uninitialize()


if __name__ == "__main__":
    sys.exit(main())
