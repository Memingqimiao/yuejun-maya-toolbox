# -*- coding: utf-8 -*-
"""Copy real library resources into a disposable project and verify local paths."""
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
    root = tempfile.mkdtemp(prefix="YuejunProjectAssets_")
    report = {"project": root, "assets": []}
    try:
        config.resource_root = lambda: "C:/Yuejun_ToolBox"
        cmds.workspace(root, newWorkspace=True)
        for key, value in (("scene", "scenes"), ("sourceImages", "sourceimages"), ("images", "images"),
                           ("renderData", "renderData"), ("fileCache", "cache/nCache")):
            cmds.workspace(fileRule=(key, value))
            os.makedirs(os.path.join(root, value), exist_ok=True)
        cmds.workspace(saveWorkspace=True)
        cmds.workspace(root, openWorkspace=True)
        cmds.loadPlugin("mtoa", quiet=True)
        cmds.loadPlugin("vrayformaya", quiet=True)
        for key in ("preset_arnold", "preset_vray", "import_eye", "disp", "import_growth"):
            cmds.file(new=True, force=True)
            result = core.execute(key)
            paths, errors = project.dependencies()
            invalid = []
            for plug, (raw, _) in paths.items():
                resolved = raw if os.path.isabs(raw) else os.path.join(root, raw)
                if not project.inside(resolved, root) or not project.pattern_files(resolved):
                    invalid.append([plug, raw])
            if key == "preset_arnold":
                manifest = os.path.join(root, "data/Yuejun/sync_manifest.json")
                with open(manifest, "r", encoding="utf-8") as stream:
                    index = json.load(stream)
                before = {entry["target"]: os.stat(os.path.join(root, entry["target"])).st_mtime_ns for entry in index.values()}
                core.open_scene_preset(config.TOOLS[key].path, discard_changes=True)
                assert all(os.stat(os.path.join(root, path)).st_mtime_ns == timestamp for path, timestamp in before.items())
            report["assets"].append({"key": key, "result": result, "path_count": len(paths),
                                      "invalid": invalid, "scan_errors": errors})
        report["success"] = all(not item["invalid"] and not item["scan_errors"] for item in report["assets"])
    finally:
        with open("dist/project_asset_validation.json", "w", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
        maya.standalone.uninitialize()
    return 0 if report.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
