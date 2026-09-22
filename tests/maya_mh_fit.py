# -*- coding: utf-8 -*-
"""Run in disposable Maya 2022 mayapy with local MetaHuman FBX assets."""
import os
import sys
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    import maya.standalone
    maya.standalone.initialize(name="python")
    from maya import cmds
    from maya.api import OpenMaya as om
    from yuejun_toolbox import config, core, mh_fit as fit, metahuman as mh
    config.set_resource_root("C:/Yuejun_ToolBox")
    folder = tempfile.mkdtemp(prefix="yj_fit_test_")
    cmds.workspace(folder, newWorkspace=True)
    for key, value in (("scene", "scenes"), ("sourceImages", "sourceimages"), ("images", "images"), ("renderData", "renderData")):
        cmds.workspace(fileRule=(key, value))
    cmds.workspace(saveWorkspace=True)
    cmds.undoInfo(state=True)
    sex = os.environ.get("YUEJUN_TEST_SEX", "Female")
    refs = fit.reference(sex)
    ref = core.mesh(refs["head"])[2]
    original = ref.getPoints(om.MSpace.kWorld)
    count = ref.numVertices
    # Reverse vertex indices but preserve face winding and original UV assignments.
    counts, vertices = ref.getVertices()
    changed = [om.MPoint(p.x * 1.1, p.y * 1.1 + 3, p.z * 1.1) for p in original]
    new = om.MFnMesh()
    obj = new.create(list(reversed(changed)), counts, [count - 1 - i for i in vertices])
    new.setUVs(*ref.getUVs("map1"))
    new.assignUVs(*ref.getAssignedUVs("map1"))
    target = cmds.rename(cmds.listRelatives(new.fullPathName(), parent=True, fullPath=True)[0], "Custom_Shuffled_Head")
    cmds.sets(target, edit=True, forceElement="initialShadingGroup")
    cmds.select(target)
    before = [tuple(p) for p in core.mesh(target)[2].getPoints()]
    print(fit.repair_indices(sex))
    repaired = cmds.ls(selection=True, long=True)[0]
    fixed_fn = core.mesh(repaired)[2]
    assert mh.topology_signature(fixed_fn) == mh.topology_signature(ref)
    assert all(a.distanceTo(b) < 1e-5 for a, b in zip(fixed_fn.getPoints(om.MSpace.kWorld), changed))
    cmds.undo()
    assert not cmds.objExists(repaired)
    cmds.redo()
    assert cmds.objExists(repaired)
    assert all(a.distanceTo(b) < 1e-5 for a, b in zip(core.mesh(repaired)[2].getPoints(om.MSpace.kWorld), changed))
    cmds.select(target)
    print(fit.generate(sex))
    roots = cmds.ls("*." + fit.SOURCE, objectsOnly=True, long=True)
    assert len(roots) == 1
    import json
    outputs = json.loads(cmds.getAttr(roots[0] + "." + fit.OUTPUT))
    assert len(outputs) == 8
    for part, uid in outputs.items():
        points = core.mesh(mh._resolve(uid))[2].getPoints(om.MSpace.kWorld)
        source = core.mesh(refs[part])[2].getPoints(om.MSpace.kWorld)
        error = max(a.distanceTo(om.MPoint(b.x * 1.1, b.y * 1.1 + 3, b.z * 1.1)) for a, b in zip(points, source))
        assert error < 3e-4, (part, error)
    cmds.undo()
    assert not cmds.ls("*." + fit.SOURCE, objectsOnly=True)
    cmds.redo()
    assert len(cmds.ls("*." + fit.SOURCE, objectsOnly=True)) == 1
    cmds.select(target)
    print(fit.generate(sex))
    assert len(cmds.ls("*." + fit.SOURCE, objectsOnly=True)) == 1
    assert before == [tuple(p) for p in core.mesh(target)[2].getPoints()]
    # Rigid rotation must also rotate eyeballs / teeth rather than just move them.
    previous = {p: core.mesh(mh._resolve(uid))[2].getPoints(om.MSpace.kWorld) for p,uid in outputs.items()}
    cmds.setAttr(target + ".rotate", 12, 18, -7)
    cmds.select(target)
    print(fit.generate(sex))
    matrix = core.mesh(target)[2].dagPath().inclusiveMatrix()
    for part,uid in outputs.items():
        actual = core.mesh(mh._resolve(uid))[2].getPoints(om.MSpace.kWorld)
        error = max(a.distanceTo(b * matrix) for a,b in zip(actual,previous[part]))
        assert error < 0.002, (part, error)
    scene = os.path.join(folder, "fit_roundtrip.ma")
    cmds.file(rename=scene)
    cmds.file(save=True, type="mayaAscii")
    cmds.file(scene, open=True, force=True)
    cmds.select(target)
    print(fit.generate(sex))
    assert len(cmds.ls("*." + fit.SOURCE, objectsOnly=True)) == 1
    # A local sculpt around one eye must move that accessory, not only global transforms.
    eye = core.mesh(mh._resolve(outputs["eyeLeft"]))[2]
    eye_points = eye.getPoints(om.MSpace.kWorld)
    center = om.MVector()
    for point in eye_points:
        center += om.MVector(point)
    center /= len(eye_points)
    source_fn = core.mesh(target)[2]
    import math
    sculpted = []
    for point in source_fn.getPoints(om.MSpace.kWorld):
        distance = (om.MVector(point) - center).length()
        sculpted.append(point + om.MVector(0, 0.3 * math.exp(-distance*distance / 16), 0))
    fit.write_points([(core.mesh(target)[1], sculpted)])
    cmds.select(target)
    fit.generate(sex)
    eye_after = core.mesh(mh._resolve(outputs["eyeLeft"]))[2].getPoints(om.MSpace.kWorld)
    assert sum(b.y-a.y for a,b in zip(eye_points,eye_after)) / len(eye_after) > 0.05
    # Invalid UVs fail before an existing output is edited.
    cmds.polyEditUV(target + ".map[0]", uValue=0.1)
    cmds.select(target)
    try:
        fit.generate(sex)
        raise AssertionError("Changed UV accepted")
    except core.ToolError:
        pass
    print("MH_FIT_OK: shuffled IDs, UV validation, source preserved, accessory scale/translation, reuse, undo/redo")
    cmds.file(new=True, force=True)
    maya.standalone.uninitialize()


if __name__ == "__main__":
    main()
