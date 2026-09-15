# -*- coding: utf-8 -*-
"""Drag this file into Maya, or execute it with runpy.run_path."""
import os
import sys
import importlib


def launch():
    root = os.path.dirname(os.path.abspath(__file__))
    loaded = sys.modules.get("yuejun_toolbox")
    expected = os.path.normcase(os.path.realpath(os.path.join(root, "yuejun_toolbox")))
    if loaded is not None:
        current = os.path.normcase(os.path.realpath(os.path.dirname(loaded.__file__)))
        if current != expected:
            loaded.close()
            for name in list(sys.modules):
                if name == "yuejun_toolbox" or name.startswith("yuejun_toolbox."):
                    del sys.modules[name]
    if root in sys.path:
        sys.path.remove(root)
    sys.path.insert(0, root)
    importlib.invalidate_caches()
    toolbox = importlib.import_module("yuejun_toolbox")
    importlib.reload(toolbox)
    result = toolbox.reload_toolbox()
    print("[Yuejun Toolbox {}] {}".format(toolbox.__version__, toolbox.__file__))
    return result


def onMayaDroppedPythonFile(*args):
    return launch()


if __name__ == "__main__":
    launch()
