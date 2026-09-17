# -*- coding: utf-8 -*-
"""Disposable mayapy integration test. Args: template library output_project.

Requires licensed local VFace 074 and 115 assets; never run in a working scene.
Creates project copies, but does not save over the template or source assets.
"""
import os
import sys
import maya.standalone
maya.standalone.initialize(name="python")
from maya import cmds
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from yuejun_toolbox import vface, project, config, core, preview


def main():
    template, library, output = map(os.path.abspath, sys.argv[1:4])
    os.makedirs(output, exist_ok=True)
    cmds.workspace(output, newWorkspace=True)
    for rule, folder in (("scene", "scenes"), ("sourceImages", "sourceimages"), ("images", "images")):
        cmds.workspace(fileRule=(rule, folder))
        os.makedirs(os.path.join(output, folder), exist_ok=True)
    cmds.workspace(saveWorkspace=True)
    cmds.optionVar(stringValue=(config.ROOT_OPTION, os.path.dirname(os.path.dirname(os.path.dirname(template)))))
    cmds.file(template, open=True, force=True, executeScriptNodes=False)
    target, original, _, _ = vface.validate_scene()
    original_path = cmds.getAttr("file4.fileTextureName")
    ids = {n: cmds.getAttr(n + ".fileTextureName") for n in cmds.ls(type="file")
           if "ID_mask" in (cmds.getAttr(n + ".fileTextureName") or "")}
    source = os.path.join(library, "115")
    cmds.loadPlugin("objExport", quiet=True)
    imported = cmds.file(vface.assets(source)["geometry"], i=True, type="OBJ", returnNewNodes=True)
    source_shape = next(n for n in imported if cmds.objExists(n) and cmds.nodeType(n) == "mesh")
    source_parent, _, source_mesh = core.mesh(source_shape)
    expected_uv = tuple(tuple(values) for values in source_mesh.getUVs())
    expected_assignment = tuple(tuple(values) for values in source_mesh.getAssignedUVs())
    cmds.delete(source_parent)
    print(vface.apply(source))
    current = vface.validate_scene()[1]
    assert current != original
    current_mesh = core.mesh(current)[2]
    assert tuple(tuple(values) for values in current_mesh.getUVs()) == expected_uv
    assert tuple(tuple(values) for values in current_mesh.getAssignedUVs()) == expected_assignment
    assert cmds.isConnected("file2.outColorR", "displacementShader1.displacement")
    for node in ("file2", "file4", vface.UTILITY):
        path = cmds.getAttr(node + ".fileTextureName")
        resolved = path if os.path.isabs(path) else os.path.join(output, path)
        assert project.inside(resolved, output), path
        assert os.path.isfile(resolved), path
    cmds.undo()
    assert vface.validate_scene()[1] == original
    assert cmds.getAttr("file4.fileTextureName") == original_path
    cmds.redo()
    print("REDO_SHAPE",current,vface.validate_scene()[1])
    print("GROUPS",cmds.ls("VFace*",long=True,type="transform"))
    assert vface.validate_scene()[1] == current
    count = len(cmds.ls(type="mesh"))
    print(vface.apply(source))
    assert len(cmds.ls(type="mesh")) == count
    print(vface.apply(os.path.join(library, "074")))
    head074 = vface.validate_scene()[1]
    assert head074 != current
    print(vface.apply(source))
    assert vface.validate_scene()[1] == current
    assert len(cmds.ls(type="mesh")) == count + 13
    cmds.undo()
    assert vface.validate_scene()[1] == head074
    cmds.redo()
    assert vface.validate_scene()[1] == current
    assert ids == {n: cmds.getAttr(n + ".fileTextureName") for n in ids}
    # A user lock must refuse the operation before changing the active head.
    cmds.setAttr("file4.fileTextureName", lock=True)
    try:
        vface.apply(os.path.join(library, "074"))
    except Exception as error:
        assert "file4.fileTextureName" in str(error), str(error)
    else:
        raise AssertionError("Locked texture was not refused")
    cmds.setAttr("file4.fileTextureName", lock=False)
    assert vface.validate_scene()[1] == current
    consumer = cmds.createNode("mesh", name="VFaceTestConsumerShape")
    consumer_parent = cmds.listRelatives(consumer, parent=True)[0]
    cmds.connectAttr(current + ".outMesh", consumer + ".inMesh")
    try:
        vface.apply(os.path.join(library, "074"))
    except core.ToolError as error:
        assert "XGen" in str(error), str(error)
    else:
        raise AssertionError("Connected mesh was not refused")
    cmds.delete(consumer_parent)
    # Test a third identity and inspect every companion model/group.
    print(vface.apply(os.path.join(library, "061")))
    for _, name, category in vface.EXTRAS:
        transform, shape, _, _ = vface._extra_target(name)
        assert "VFace_" + category + "_GRP" in transform, transform
        assert "061" in shape, shape
    assert cmds.getAttr("VFace_GRP.vfaceIdentity") == "061"
    for node in ("file2", "file4", vface.UTILITY, "VFace_Sclera_left_albedo", "VFace_Sclera_right_displacement"):
        assert "/VFace/061/" in cmds.getAttr(node + ".fileTextureName"), node
    print("VFACE_061_COMPANIONS_PASS")
    print("VFACE_MAYA_INTEGRATION_PASS")


try:
    main()
finally:
    maya.standalone.uninitialize()
