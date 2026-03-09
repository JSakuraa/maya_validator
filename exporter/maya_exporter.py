# exporter/maya_exporter.py

import sys

PROJECT_ROOT = "D:\\DevProjects\\maya_validator"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import maya.cmds as cmds
import maya.mel as mel

from adapters.maya_adapter import extract_scene_data
from core.validators.root_scale import RootScaleValidator
from core.validators.loop_clean import LoopCleanValidator
from core.validators.naming import NamingConventionValidator
from core.runner import ValidationRunner


# Studio canonical FBX export settings.
# These are enforced programmatically — artists cannot change them
# through the export dialog because the dialog is never shown.
CANONICAL_EXPORT_SETTINGS = {
    "scale_factor": 1.0,
    "bake_anim": True,
    "bake_step": 1.0,
}


def validate_and_export(root_joint: str, output_path: str) -> dict:
    """
    Validates the animation on root_joint and exports to output_path
    if validation passes with no error-severity failures.

    Steps:
      1. Call extract_scene_data(root_joint) to get a SceneData object
      2. Build a ValidationRunner with all three validators
      3. Run validation against the scene
      4. If runner.has_errors(results) is True, return a failure dict
         without exporting. Include the error details in "errors".
      5. If no errors, call _export_fbx(root_joint, output_path)
      6. Return a success dict with any warnings included.

    Return format on failure:
    {
        "success": False,
        "errors":  [{"rule": rule_name, "message": message}, ...],
        "asset":   scene.asset_name,
    }

    Return format on success:
    {
        "success":  True,
        "warnings": [warning_message, ...],
        "asset":    scene.asset_name,
        "path":     output_path,
    }
    """
    # Step 1: Extract scene data from Maya
    scene = extract_scene_data(root_joint)

    # Step 2: Set up validators and runner
    validators = [
        RootScaleValidator(),
        LoopCleanValidator(),
        NamingConventionValidator(),
    ]

    runner = ValidationRunner(validators)

    # Step 3: Run validation
    results = runner.run(scene)

    # Step 4: Check for errors
    if runner.has_errors(results):
        errors = [
            {"rule": r.rule_name, "message": r.message}
            for r in results
            if r.status == "fail" and r.severity == "error"
        ]
        return {
            "success": False,
            "errors": errors,
            "asset": scene.asset_name,
        }

    _export_fbx(root_joint, output_path)

    warnings = [
        r.message for r in results if r.status == "fail" and r.severity == "warning"
    ]

    return {
        "success": True,
        "warnings": warnings,
        "asset": scene.asset_name,
        "path": output_path,
    }


def _export_fbx(root_joint: str, output_path: str):
    """
    Selects the skeleton hierarchy and writes an FBX file using
    Maya's MEL-based FBX export commands.

    Steps:
      1. Select root_joint and its full hierarchy:
         cmds.select(root_joint, hierarchy=True)
      2. Reset FBX export settings to defaults:
         mel.eval("FBXResetExport")
      3. Apply each setting from CANONICAL_EXPORT_SETTINGS using
         mel.eval() with the appropriate FBXExport MEL commands.
      4. Normalize the output path (replace backslashes with forward
         slashes — MEL requires forward slashes).
      5. Export selected objects:
         mel.eval(f'FBXExport -f "{normalized_path}" -s')

    Relevant MEL commands:
      mel.eval("FBXExportBakeComplexAnimation -v true")
      mel.eval(f"FBXExportBakeComplexStep -v {step}")
      mel.eval(f"FBXExportScaleFactor {scale}")
      mel.eval("FBXExportFileVersion -v FBX201800")
      mel.eval("FBXExportInAscii -v false")
      mel.eval("FBXExportSmoothingGroups -v false")
    """
    cmds.select(root_joint, hierarchy=True)

    mel.eval("FBXResetExport")  # reset to defaults first
    mel.eval("FBXExportSmoothingGroups -v false")
    mel.eval("FBXExportHardEdges -v false")
    mel.eval("FBXExportTangents -v false")
    mel.eval("FBXExportSmoothMesh -v false")
    mel.eval("FBXExportInstances -v false")
    mel.eval(
        f"FBXExportBakeComplexAnimation -v {str(CANONICAL_EXPORT_SETTINGS['bake_anim']).lower()}"
    )
    mel.eval(f"FBXExportBakeComplexStep -v {CANONICAL_EXPORT_SETTINGS['bake_step']}")
    mel.eval(f"FBXExportScaleFactor {CANONICAL_EXPORT_SETTINGS['scale_factor']}")
    mel.eval("FBXExportFileVersion -v FBX201800")
    mel.eval("FBXExportInAscii -v false")

    normalized_path = output_path.replace("\\", "/")

    mel.eval(f'FBXExport -f "{normalized_path}" -s')
