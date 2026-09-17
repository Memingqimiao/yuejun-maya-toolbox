# -*- coding: utf-8 -*-
"""Maya 2022 / Python 3.7 toolbox. Importing does not create a window."""

__version__ = "3.7.5"


def show():
    from . import ui
    return ui.show()


def close():
    from . import ui
    ui.close()


def reload_toolbox():
    """Delete old callbacks with their window before reloading dependencies."""
    import importlib
    from . import config, preview, project, core, eyes, vface, vface_ui, notes_data, notes, ui
    ui.close()
    importlib.invalidate_caches()
    for module in (config, preview, project, core, eyes, vface, vface_ui, notes_data, notes, ui):
        importlib.reload(module)
    return ui.show()
