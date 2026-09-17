# -*- coding: utf-8 -*-
"""Build one pasteable Python script from the maintained config/core/UI sources."""
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
VERSION = "3.7.5"
LOADER = 'def _yj_launch(sources=_yj_sources, sys=_yj_sys, types=_yj_types):\n    from maya import cmds\n    for name in ("yuejun_toolbox.ui", "_yuejun_single.ui"):\n        previous = sys.modules.get(name)\n        if previous is not None:\n            previous.close()\n    for window in ("yuejunToolbox", "myWindow"):\n        if cmds.window(window, exists=True):\n            cmds.deleteUI(window)\n    package_name = "_yuejun_single"\n    package = types.ModuleType(package_name)\n    package.__path__ = []\n    package.__package__ = package_name\n    package.__version__ = "3.7.5"\n    sys.modules[package_name] = package\n    for name in ("config", "preview", "project", "core", "eyes", "vface", "vface_ui", "notes_data", "notes", "ui"):\n        fullname = package_name + "." + name\n        module = types.ModuleType(fullname)\n        module.__package__ = package_name\n        module.__file__ = "<Yuejun single script/" + name + ".py>"\n        sys.modules[fullname] = module\n        setattr(package, name, module)\n        exec(compile(sources[name], module.__file__, "exec"), module.__dict__)\n    package.reload_toolbox = _yj_launch\n    package.close = package.ui.close\n    package.show = package.ui.show\n    return package.show()\n\n\ndef onMayaDroppedPythonFile(*args):\n    return _yj_launch()\n\n\nif __name__ == "__main__":\n    _yj_launch()\n'

def main():
    parts = ["# -*- coding: utf-8 -*-\n# Yuejun Toolbox " + VERSION + " - Paste all into Maya's Python tab.\nimport sys as _yj_sys\nimport types as _yj_types\n_yj_sources = {}\n"]
    for name in ("config", "preview", "project", "core", "eyes", "vface", "vface_ui", "notes_data", "notes", "ui"):
        source = (ROOT / "yuejun_toolbox" / (name + ".py")).read_text(encoding="utf-8")
        quote = "'" * 3
        if quote in source:
            raise ValueError("Embedded source contains triple single quotes")
        parts.append("_yj_sources[%r] = r%s\n%s\n%s\n" % (name, quote, source, quote))
    parts.append(LOADER)
    output = ROOT / "dist" / ("YuejunToolbox_" + VERSION.replace(".", "_") + "_Single.py")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(parts), encoding="utf-8")
    print(output)

if __name__ == "__main__":
    main()
