# -*- coding: utf-8 -*-
"""Read a real preset in an isolated mayapy process; never run in a live scene."""
import argparse
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--key", default="preset_arnold")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    import maya.standalone
    maya.standalone.initialize(name="python")
    from maya import cmds
    from yuejun_toolbox import config, core
    report = {"key": args.key, "maya": cmds.about(version=True), "python": sys.version}
    try:
        config.resource_root = lambda: args.root
        renderer = {"preset_arnold": "mtoa", "preset_vray": "vrayformaya", "disp_rs": "redshift4maya"}.get(args.key)
        if renderer:
            cmds.loadPlugin(renderer, quiet=True)
        cmds.file(new=True, force=True)
        cmds.undoInfo(state=True)
        cmds.polyCube(name="UserSceneSentinel", constructionHistory=False)
        report["operation"] = config.TOOLS[args.key].kind
        if report["operation"] == "open":
            saved_work = os.path.join(os.path.dirname(args.output), "UserWork.ma")
            core.save_scene(saved_work)
            report["previous_scene_saved"] = os.path.isfile(saved_work)
        try:
            report["result"] = core.execute(args.key)
            report["success"] = True
        except Exception:
            report["success"] = False
            report["error"] = traceback.format_exc()
        report["sentinel_preserved"] = cmds.objExists("UserSceneSentinel")
        report["residual_namespaces"] = [name for name in
            (cmds.namespaceInfo(":", listOnlyNamespaces=True, recurse=True, absoluteName=True) or [])
            if "_YuejunImport_" in name]
        report["node_count"] = len(cmds.ls() or [])
        report["active_file"] = cmds.file(query=True, sceneName=True)
        report["namespaced_node_count"] = sum(":" in node.rsplit("|", 1)[-1] for node in (cmds.ls(long=True) or []))
    except Exception:
        report["success"] = False
        report["error"] = traceback.format_exc()
    finally:
        with open(args.output, "w", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
        maya.standalone.uninitialize()
    return 0 if report.get("success") and not report.get("residual_namespaces") else 1


if __name__ == "__main__":
    sys.exit(main())
