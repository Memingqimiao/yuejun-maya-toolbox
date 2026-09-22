# Project instructions

Stable version: 3.7.14, based on the user-selected 3.7.1. Scene presets OPEN a scene; do not reintroduce the abandoned 3.8.0 merge/import experiment without a new user request.

Target Maya 2022, Python 3.7, maya.cmds and OpenMaya 2.0. Keep UI separate from scene logic. Preserve preview save protection and module reloading. Handle failures gracefully and use undoable scene operations where supported.

Edit maintained modules in yuejun_toolbox, then run `python scripts/build_single.py`. Never edit the generated script independently. Run `python -m unittest discover -s tests -p "test_*.py" -q`. Maya integration scripts require a separate disposable Maya session and local assets.

Keep resource files out of Git. Do not convert ma/mb formats just to rename a file. Resource roots are configured by the user on each machine.

Read README.md and docs/DEVELOPMENT.md before changing behavior. No API credentials, machine logs, commercial assets or personal attachments belong in this repository.
