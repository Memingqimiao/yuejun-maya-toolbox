# -*- coding: utf-8 -*-
"""Build one pasteable Python script from the maintained config/core/UI sources."""
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = "3.7.13"
MODULES = ("config", "preview", "project", "core", "eyes", "gn", "metahuman", "vface", "vface_ui",
           "notes_data", "notes", "ui")

LOADER = '''def _yj_launch(sources=_yj_sources, sys=_yj_sys, types=_yj_types):
    from maya import cmds
    for name in ("yuejun_toolbox.ui", "_yuejun_single.ui"):
        previous = sys.modules.get(name)
        if previous is not None:
            previous.close()
    for window in ("yuejunToolbox", "myWindow"):
        if cmds.window(window, exists=True):
            cmds.deleteUI(window)
    package_name = "_yuejun_single"
    package = types.ModuleType(package_name)
    package.__path__ = []
    package.__package__ = package_name
    package.__version__ = "{version}"
    sys.modules[package_name] = package
    for name in {modules}:
        fullname = package_name + "." + name
        module = types.ModuleType(fullname)
        module.__package__ = package_name
        module.__file__ = "<Yuejun single script/" + name + ".py>"
        sys.modules[fullname] = module
        setattr(package, name, module)
        exec(compile(sources[name], module.__file__, "exec"), module.__dict__)
    package.reload_toolbox = _yj_launch
    package.close = package.ui.close
    package.show = package.ui.show
    return package.show()


def onMayaDroppedPythonFile(*args):
    return _yj_launch()


if __name__ == "__main__":
    _yj_launch()
'''


def main():
    # A non-ASCII checkout path must not crash the build on a default Windows console.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parts = ["# -*- coding: utf-8 -*-\n# Yuejun Toolbox " + VERSION +
             " - Paste all into Maya's Python tab.\nimport sys as _yj_sys\n"
             "import types as _yj_types\n_yj_sources = {}\n"]
    for name in MODULES:
        source = (ROOT / "yuejun_toolbox" / (name + ".py")).read_text(encoding="utf-8")
        quote = "'" * 3
        if quote in source:
            raise ValueError("Embedded source contains triple single quotes")
        parts.append("_yj_sources[%r] = r%s\n%s\n%s\n" % (name, quote, source, quote))
    parts.append(LOADER.format(version=VERSION, modules=repr(MODULES)))
    output = ROOT / "dist" / ("YuejunToolbox_" + VERSION.replace(".", "_") + "_Single.py")
    output.parent.mkdir(parents=True, exist_ok=True)
    with io.open(str(output), "w", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(parts))
    print(output)


if __name__ == "__main__":
    main()
