# -*- coding: utf-8 -*-
"""Disposable mayapy integration test. Requires YUEJUN_TOOLBOX_ROOT assets."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    import maya.standalone
    maya.standalone.initialize(name="python")
    from maya import cmds
    from yuejun_toolbox import config, metahuman as mh
    config.set_resource_root(os.environ.get("YUEJUN_TOOLBOX_ROOT", "C:/Yuejun_ToolBox"))
    folder = tempfile.mkdtemp(prefix="yuejun_mh_test_")
    cmds.workspace(folder, newWorkspace=True)
    for rule, value in (("scene", "scenes"), ("sourceImages", "sourceimages"),
                        ("images", "images"), ("renderData", "renderData")):
        cmds.workspace(fileRule=(rule, value))
    cmds.workspace(saveWorkspace=True)
    cmds.undoInfo(state=True)
    def snapshot(root):
        records = [mh._snapshot(s) for s in mh._meshes(root)]
        for record in records:
            record["groups"] = sorted(record["groups"])
        return records

    original_count = len(cmds.ls(type="mesh"))
    mh.import_model("Female")
    assert len(cmds.ls(type="mesh")) == original_count + 10
    female = mh.target()
    assert len(mh._meshes(female)) == 5
    shape = mh._meshes(female)[0]
    extra = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="Test_Face_MaterialSG")
    cmds.sets(shape + ".f[0:3]", edit=True, forceElement=extra)
    cmds.select(female)
    originals = snapshot(female)
    # Import a second copy and a male into the same scene: prior nodes unchanged.
    mh.import_model("Female")
    assert len(mh._meshes(mh.target())) == 5
    mh.import_model("Male")
    male = mh.target()
    assert len(mh._meshes(male)) == 5
    assert len(cmds.ls(type="mesh")) == original_count + 30
    assert originals == snapshot(female)
    cmds.select(female)
    mh.apply()
    files = cmds.ls(type="file")
    for node in files:
        path = cmds.getAttr(node + ".fileTextureName")
        assert os.path.isfile(path), path
        assert os.path.commonpath([folder, os.path.normpath(path)]) == folder
    mh.apply()
    assert cmds.ls(type="file") == files
    mh.restore()
    for record in originals:
        shape = mh._resolve(record["mesh"])
        actual = {mh._uuid(sg) for sg in cmds.listConnections(shape, type="shadingEngine") or []}
        expected = {uid for uid, faces in record["groups"] if faces}
        assert actual == expected, (shape, actual, expected)
    assert originals == snapshot(female)
    cmds.undo()
    assert cmds.getAttr(female + "." + mh.BACKUP)
    cmds.redo()
    assert not cmds.getAttr(female + "." + mh.BACKUP)
    mh.apply()
    female = cmds.rename(female, "Renamed_Female")
    path = os.path.join(folder, "roundtrip.ma")
    cmds.file(rename=path)
    cmds.file(save=True, type="mayaAscii")
    cmds.file(path, open=True, force=True)
    cmds.select(female)
    mh.restore()
    for record in originals:
        shape = mh._resolve(record["mesh"])
        actual = {mh._uuid(sg) for sg in cmds.listConnections(shape, type="shadingEngine") or []}
        expected = {uid for uid, faces in record["groups"] if faces}
        assert actual == expected, (shape, actual, expected)
    assert originals == snapshot(female)
    # Male is independently addressable after round-trip.
    cmds.select(male)
    mh.apply()
    mh.restore()
    # Reproduce a scene restored by 3.7.10 (face assignments + stale whole SG).
    cmds.select(female)
    mh.apply()
    import json
    legacy_backup = json.loads(cmds.getAttr(female + "." + mh.BACKUP))
    for record in legacy_backup:
        shape = mh._resolve(record["mesh"])
        for uid, faces in record["groups"]:
            if faces:
                cmds.sets(mh._members(shape, faces), edit=True, forceElement=mh._resolve(uid))
    mh._string(female, mh.BACKUP, "")
    cmds.select(female)
    mh.toggle_textures()
    mh.toggle_textures()
    for record in originals:
        actual = {mh._uuid(sg) for sg in cmds.listConnections(mh._resolve(record["mesh"]), type="shadingEngine") or []}
        assert actual == {uid for uid, faces in record["groups"] if faces}
    # Toggle materials twice, including after previous restore.
    cmds.select(male)
    mh.toggle_textures()
    assert cmds.getAttr(male + "." + mh.BACKUP)
    mh.toggle_textures()
    assert not cmds.getAttr(male + "." + mh.BACKUP)
    # Any head name is accepted, topology IDs remain required.
    head = next(s for s in mh._meshes(male) if cmds.getAttr(s + "." + mh.ROLE) == "Head")
    transform = cmds.listRelatives(head, parent=True, fullPath=True)[0]
    transform = cmds.rename(transform, "Arbitrary_Head_Name")
    from yuejun_toolbox import core
    def uv_snapshot():
        fn = core.mesh(transform)[2]
        return ([list(v) for v in fn.getUVs()], [list(v) for v in fn.getAssignedUVs()])
    before_uv = uv_snapshot()
    cmds.select(transform)
    mh.toggle_uv()
    cut_uv = uv_snapshot()
    assert cut_uv != before_uv
    cmds.undo()
    assert uv_snapshot() == before_uv
    cmds.redo()
    assert uv_snapshot() == cut_uv
    # UV backup must survive saving and reloading too.
    cmds.file(save=True, type="mayaAscii")
    cmds.file(path, open=True, force=True)
    cmds.select(transform)
    mh.toggle_uv()
    assert uv_snapshot() == before_uv
    cmds.undo()
    assert uv_snapshot() == cut_uv
    cmds.redo()
    assert uv_snapshot() == before_uv
    mh.toggle_uv()
    mh.toggle_uv()
    assert uv_snapshot() == before_uv
    # Soft selection must neither expand affected UVs nor change user settings.
    cmds.softSelect(softSelectEnabled=True, softSelectDistance=50.0, softSelectFalloff=1)
    cmds.select(transform)
    mh.toggle_uv()
    assert uv_snapshot() == cut_uv
    assert cmds.softSelect(query=True, softSelectEnabled=True)
    assert cmds.softSelect(query=True, softSelectDistance=True) == 50.0
    mh.toggle_uv()
    assert uv_snapshot() == before_uv
    assert cmds.softSelect(query=True, softSelectEnabled=True)
    # Failure in a command must also restore soft selection.
    from unittest.mock import patch
    with patch.object(cmds, "polyMapCut", side_effect=RuntimeError("test failure")):
        try:
            mh.toggle_uv()
            raise AssertionError("Expected failure")
        except RuntimeError:
            pass
    assert cmds.softSelect(query=True, softSelectEnabled=True)
    assert uv_snapshot() == before_uv
    cmds.softSelect(softSelectEnabled=False)
    # Actual supplied MetaHuman head/body, including a transformed parent.
    from maya.api import OpenMaya as om
    shapes = mh._meshes(male)
    head = next(s for s in shapes if cmds.getAttr(s + "." + mh.ROLE) == "Head")
    body = next(s for s in shapes if cmds.getAttr(s + "." + mh.ROLE) == "Body")
    cmds.setAttr(male + ".rotate", 23, 14, 7)
    cmds.setAttr(male + ".scale", 1.2, 0.8, 1.1)
    def mesh_data(shape):
        fn = core.mesh(shape)[2]
        return ([tuple(v) for v in fn.getPoints(om.MSpace.kWorld)],
                [tuple(v) for v in fn.getNormals(om.MSpace.kWorld)])
    before_seam = [mesh_data(s) for s in (head, body)]
    cmds.select([body, head])
    cmds.softSelect(softSelectEnabled=True)
    print(mh.fix_seams())
    assert cmds.softSelect(query=True, softSelectEnabled=True)
    fa, fb = [core.mesh(s)[2] for s in (head, body)]
    pairs = mh.seam_pairs(fa.getPoints(om.MSpace.kWorld), mh.boundary_vertices(fa),
                         fb.getPoints(om.MSpace.kWorld), mh.boundary_vertices(fb), 0.01)
    assert pairs
    for i, j in pairs:
        va = om.MItMeshVertex(fa.dagPath()); va.setIndex(i)
        vb = om.MItMeshVertex(fb.dagPath()); vb.setIndex(j)
        na = va.getNormals(om.MSpace.kWorld)
        nb = vb.getNormals(om.MSpace.kWorld)
        assert all((om.MVector(a).normal() - om.MVector(b).normal()).length() < 1e-5 for a in na for b in nb)
    assert [mesh_data(s)[0] for s in (head, body)] == [item[0] for item in before_seam]
    cmds.undo()
    after_undo = [mesh_data(s) for s in (head, body)]
    for old, restored in zip(before_seam, after_undo):
        assert len(old[1]) == len(restored[1])
        assert all(abs(x-y) < 1e-6 for a,b in zip(old[1], restored[1]) for x,y in zip(a,b))
    cmds.redo()
    print("SEAMS_OK: actual assets, world normals with rotation/nonuniform scale, unchanged positions, undo/redo")
    cube = cmds.polyCube()[0]
    cmds.select(cube)
    try:
        mh.toggle_uv()
        raise AssertionError("Wrong topology accepted")
    except core.ToolError:
        pass
    print("METAHUMAN_TOGGLES_OK: textures, arbitrary head name, exact UV restore, undo/redo, save/reopen, topology rejection")
    print("METAHUMAN_INTEGRATION_OK: imports, collisions, local textures, idempotency, restore, undo/redo, save/reopen")
    cmds.file(new=True, force=True)
    maya.standalone.uninitialize()


if __name__ == "__main__":
    main()
