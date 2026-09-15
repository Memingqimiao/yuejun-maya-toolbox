"""Verify an Arnold preset in an isolated Maya process, without saving it."""
import argparse
import json
import os
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    import maya.standalone
    maya.standalone.initialize(name="python")
    from maya import cmds
    report = {}
    try:
        cmds.loadPlugin("mtoa", quiet=True)
        cmds.file(args.scene, open=True, force=True, executeScriptNodes=False)
        textures = []
        for node in cmds.ls(type="file") or []:
            path = cmds.getAttr(node + ".fileTextureName")
            textures.append({"node": node, "path": path, "exists": os.path.isfile(path)})
        report = {"maya": cmds.about(version=True), "textures": textures,
                  "renderer": cmds.getAttr("defaultRenderGlobals.currentRenderer"),
                  "resolution": [cmds.getAttr("defaultResolution." + attr) for attr in ("width", "height")],
                  "node_count": len(cmds.ls()),
                  "unknown_nodes": cmds.ls(type="unknown") or [],
                  "aovs": cmds.ls(type="aiAOV") or [],
                  "missing_textures": [item for item in textures if not item["exists"]]}
        report["success"] = not report["missing_textures"] and report["renderer"] == "arnold"
    finally:
        with open(args.output, "w", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
        maya.standalone.uninitialize()
    return 0 if report.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
