# -*- coding: utf-8 -*-
"""Exercise both real eye assets in a disposable Maya project."""
import json
import os
import sys
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    import maya.standalone
    maya.standalone.initialize(name="python")
    from maya import cmds
    from yuejun_toolbox import config, core, project
    root = tempfile.mkdtemp(prefix="YuejunEye350_")
    report = {"project": root, "assets": []}
    try:
        config.resource_root = lambda: "C:/Yuejun_ToolBox"
        cmds.workspace(root, newWorkspace=True)
        for key, value in (("scene", "scenes"), ("sourceImages", "sourceimages"), ("images", "images"), ("renderData", "renderData")):
            cmds.workspace(fileRule=(key, value))
            os.makedirs(os.path.join(root, value), exist_ok=True)
        cmds.workspace(saveWorkspace=True)
        cmds.workspace(root, openWorkspace=True)
        cmds.loadPlugin("mtoa", quiet=True)
        cmds.loadPlugin("vrayformaya", quiet=True)
        for key in ("import_eye", "import_eye_arnold"):
            cmds.file(new=True, force=True)
            result = core.execute(key)
            paths, errors = project.dependencies()
            invalid = []
            for plug, (raw, _) in paths.items():
                path = raw if os.path.isabs(raw) else os.path.join(root, raw)
                if not project.inside(path, root) or not project.pattern_files(path):
                    invalid.append([plug, raw])
            index_path = os.path.join(root, "data/Yuejun/sync_manifest.json")
            with open(index_path, "r", encoding="utf-8") as stream:
                index = json.load(stream)
            before = {entry["target"]: os.stat(os.path.join(root, entry["target"])).st_mtime_ns for entry in index.values()}
            cmds.file(new=True, force=True)
            repeated = core.execute(key)
            unchanged = all(os.stat(os.path.join(root, path)).st_mtime_ns == stamp for path, stamp in before.items())
            report["assets"].append({"key": key, "result": result, "repeated": repeated,
                                      "path_count": len(paths), "invalid": invalid,
                                      "scan_errors": errors, "repeat_did_not_write": unchanged})
        report["success"] = all(not item["invalid"] and not item["scan_errors"] and item["repeat_did_not_write"] for item in report["assets"])
    finally:
        with open("dist/eye_350_validation.json", "w", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
        maya.standalone.uninitialize()
    return 0 if report.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
