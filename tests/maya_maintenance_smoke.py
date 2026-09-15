# -*- coding: utf-8 -*-
"""Disposable scene tests; run only in a separate Maya 2022 mayapy process."""
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    import maya.standalone
    maya.standalone.initialize(name="python")
    from maya import cmds
    from yuejun_toolbox import core

    class MaintenanceTests(unittest.TestCase):
        def setUp(self):
            cmds.file(new=True, force=True)
            cmds.undoInfo(state=True)

        def test_unknown_delete_is_undoable_and_locked_node_survives(self):
            bad = cmds.createNode("unknown", name="UnknownDisposable")
            locked = cmds.createNode("unknown", name="UnknownLocked")
            cmds.lockNode(locked, lock=True)
            healthy = cmds.createNode("network", name="Healthy")
            core.clean_unknown_nodes()
            self.assertFalse(cmds.objExists(bad))
            self.assertTrue(cmds.objExists(locked))
            self.assertTrue(cmds.objExists(healthy))
            cmds.undo()
            self.assertTrue(cmds.objExists(bad))

        def test_unknown_parent_with_healthy_child_survives(self):
            parent = cmds.createNode("unknownTransform", name="UnknownParent")
            child = cmds.createNode("transform", parent=parent, name="HealthyChild")
            core.clean_unknown_nodes()
            self.assertTrue(cmds.objExists(parent))
            self.assertTrue(cmds.objExists(child))

        def test_xgen_reconnect_repeat_and_undo(self):
            cmds.loadPlugin("xgenToolkit", quiet=True)
            maker = cmds.createNode("xgmMakeGuide")
            guide = cmds.createNode("xgmSplineGuide")
            self.assertTrue(cmds.objExists(guide + ".inputMesh"))
            self.assertTrue(cmds.objExists(guide + ".toMakeGuide"))
            # One surviving connection is needed to discover the guide, as in the user's command.
            cmds.connectAttr(maker + ".toGuide", guide + ".toMakeGuide")
            core.restore_xgen_guides()
            self.assertTrue(cmds.isConnected(maker + ".outputMesh", guide + ".inputMesh"))
            cmds.undo()
            self.assertFalse(cmds.isConnected(maker + ".outputMesh", guide + ".inputMesh"))
            core.restore_xgen_guides()
            core.restore_xgen_guides()
            self.assertTrue(cmds.isConnected(maker + ".outputMesh", guide + ".inputMesh"))

        def test_xgen_ambiguous_targets_are_not_guessed(self):
            cmds.loadPlugin("xgenToolkit", quiet=True)
            maker = cmds.createNode("xgmMakeGuide")
            guides = [cmds.createNode("xgmSplineGuide") for _ in range(2)]
            for guide in guides:
                cmds.connectAttr(maker + ".toGuide", guide + ".toMakeGuide")
            core.restore_xgen_guides()
            for guide in guides:
                self.assertFalse(cmds.isConnected(maker + ".outputMesh", guide + ".inputMesh"))

    try:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(MaintenanceTests))
        return 0 if result.wasSuccessful() else 1
    finally:
        maya.standalone.uninitialize()


if __name__ == "__main__":
    sys.exit(main())
