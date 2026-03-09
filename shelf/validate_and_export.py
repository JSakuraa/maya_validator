# shelf/validate_and_export.py
# HOW TO ADD THIS TO YOUR MAYA SHELF:
# 1. Open the Script Editor (Windows > General Editors > Script Editor)
# 2. Create a new Python tab
# 3. Paste this entire script into the tab
# 4. Select all the text (Ctrl+A)
# 5. Middle-mouse drag the selected text to your shelf
# 6. The button will appear on your shelf
# 7. Click it to run the full validate-and-export pipeline

import sys
import importlib

# Add project to Maya's Python path
PROJECT_ROOT = "D:\\DevProjects\\maya_validator"  # adjust this
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Force reload all modules so code changes take effect during development
# Remove these reload calls when the project is in production
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

# ── Get the selected root joint ──────────────────────────────────────────────

selection = cmds.ls(selection=True, type="joint")

if not selection:
    cmds.warning("Select a root joint first, then click Validate and Export.")
else:
    root_joint = selection[0]

    # ── Ask the artist where to save the file ────────────────────────────────

    file_result = cmds.fileDialog2(
        fileFilter="FBX Files (*.fbx)",
        dialogStyle=2,
        caption=f"Export: {root_joint}",
        fileMode=0,  # save mode
    )

    if file_result:
        output_path = file_result[0]

        # ── Run the full pipeline ─────────────────────────────────────────────

        result = validate_and_export(root_joint, output_path)

        # ── Print structured results ──────────────────────────────────────────

        print("\n" + "=" * 60)
        print(f"  Pipeline Validator — {root_joint}")
        print("=" * 60)

        if result["success"]:
            print(f"  ✓ EXPORT SUCCESSFUL")
            print(f"  Asset: {result['asset']}")
            print(f"  Path:  {result['path']}")

            if result.get("warnings"):
                print(f"\n  Warnings ({len(result['warnings'])}):")
                for w in result["warnings"]:
                    print(f"    ⚠  {w}")
            else:
                print("\n  No warnings.")

        else:
            print(f"  ✗ EXPORT BLOCKED — fix errors before exporting")
            print(f"\n  Errors ({len(result['errors'])}):")
            for e in result["errors"]:
                print(f"    ✗  [{e['rule']}]")
                print(f"       {e['message']}")

        print("=" * 60 + "\n")
