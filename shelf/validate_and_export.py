# shelf/validate_and_export.py
#
# HOW TO ADD THIS TO YOUR MAYA SHELF:
# 1. Open the Script Editor (Windows > General Editors > Script Editor)
# 2. Create a new Python tab
# 3. Paste this entire file into the tab
# 4. Select all text (Ctrl+A)
# 5. Middle-mouse drag the selected text onto your shelf
# 6. Click the resulting button to run

import sys
import importlib

PROJECT_ROOT = "C:/your/project/path/maya_validator"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Force reload all modules during development so code changes take effect.
# Remove these reload calls when the project is in production.
import core.schema
import core.runner
import core.validators.root_scale
import core.validators.loop_clean
import core.validators.naming
import adapters.maya_adapter
import exporter.maya_exporter

for mod in [
    core.schema,
    core.runner,
    core.validators.root_scale,
    core.validators.loop_clean,
    core.validators.naming,
    adapters.maya_adapter,
    exporter.maya_exporter,
]:
    importlib.reload(mod)

import maya.cmds as cmds
from exporter.maya_exporter import validate_and_export

# TODO: Get the current joint selection using cmds.ls
#       If nothing is selected, show a warning using cmds.warning and stop.
#       If something is selected, use the first item as root_joint.

# TODO: Show a file save dialog using cmds.fileDialog2 with:
#         fileFilter="FBX Files (*.fbx)"
#         dialogStyle=2
#         caption=f"Export: {root_joint}"
#         fileMode=0  (save mode)
#       If the dialog is cancelled (returns None), stop.

# TODO: Call validate_and_export(root_joint, output_path)
#       and store the result dict.

# TODO: Print structured output to the Script Editor.
#       Print a header line, then check result["success"].
#       If True:  print success message, asset name, path, and any warnings.
#       If False: print "EXPORT BLOCKED" and each error's rule and message.
