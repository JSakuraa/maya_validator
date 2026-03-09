# adapters/maya_adapter.py
#
# THIS IS THE ONLY FILE THAT IMPORTS maya.cmds.
# Every other file in this project is pure Python with no DCC dependency.
# This isolation is the core architectural decision of the pipeline.

import sys

# Add project root to Maya's Python path.
# Adjust PROJECT_ROOT to match your actual project location.
PROJECT_ROOT = "D:\\DevProjects\\maya_validator"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import maya.cmds as cmds
from core.schema import SceneData, BoneData, FCurveData, KeyframePoint


# Maps Maya attribute names to the normalized (data_path, array_index) format
# used throughout the pipeline.
#
# Maya internally identifies a curve as "root.translateX"
# The pipeline normalizes this to:
#   data_path='pose.bones["root"].location', array_index=0
#
# This translation happens here and nowhere else in the codebase.
CHANNEL_MAP = {
    "translateX": ("location", 0),
    "translateY": ("location", 1),
    "translateZ": ("location", 2),
    "rotateX": ("rotation_euler", 0),
    "rotateY": ("rotation_euler", 1),
    "rotateZ": ("rotation_euler", 2),
    "scaleX": ("scale", 0),
    "scaleY": ("scale", 1),
    "scaleZ": ("scale", 2),
}


def extract_scene_data(root_joint: str) -> SceneData:
    """
    Entry point for the Maya adapter.

    Reads a joint hierarchy and its animation curves from the live
    Maya scene and returns a SceneData object that validators consume.

    This function is the seam between Maya's world and the tool-agnostic
    validation world. Everything it returns uses normalized data_path
    strings and contains no Maya API objects.

    Args:
        root_joint: name of the root joint e.g. "root" or "hips"

    Returns:
        SceneData populated from the live Maya scene

    Hint: call the four private helpers below and pass their results
    into SceneData(). source_tool should be "maya".
    """
    all_joints = _get_joint_hierarchy(root_joint)
    bones = _extract_bones(all_joints)
    fcurves = _extract_fcurves(all_joints)
    start, end = _get_frame_range()

    return SceneData(
        bones=bones,
        fcurves=fcurves,
        frame_start=start,
        frame_end=end,
        asset_name=root_joint,
        source_tool="maya",
        fps=_get_fps(),
    )


def _get_joint_hierarchy(root_joint: str) -> list[str]:
    """
    Returns all joints in the hierarchy starting from root_joint.
    The root joint should be first in the returned list.

    Hint: cmds.listRelatives with allDescendents=True and type='joint'
    returns all descendants. Prepend root_joint to that list.
    """
    descendants = (
        cmds.listRelatives(root_joint, allDescendents=True, type="joint") or []
    )
    return [root_joint] + descendants


def _extract_bones(joints: list[str]) -> list[BoneData]:
    """
    Converts a list of joint names into BoneData objects.

    For each joint, find its parent joint using cmds.listRelatives
    with parent=True and type='joint'. If no parent joint exists,
    parent should be None (this is the root bone).

    Returns a list of BoneData objects in the same order as joints.

    Hint: cmds.listRelatives returns a list or None.
    """
    bones = []
    for joint in joints:
        parents = cmds.listRelatives(joint, parent=True, type="joint")
        parent = parents[0] if parents else None
        bones.append(BoneData(name=joint, parent=parent))
    return bones


def _extract_fcurves(joints: list[str]) -> list[FCurveData]:
    """
    Reads all animation curves for all joints in the hierarchy.

    For each joint and each channel in CHANNEL_MAP:
      1. Build the full attribute name: f"{joint}.{maya_attr}"
         e.g. "root.translateX"
      2. Check if an animCurve node is connected using cmds.listConnections
         with type='animCurve'. Skip if none.
      3. Read keyframe times with:
         cmds.keyframe(full_attr, query=True, timeChange=True)
      4. Read keyframe values with:
         cmds.keyframe(full_attr, query=True, valueChange=True)
      5. Skip if no times returned.
      6. Build the normalized data_path:
         f'pose.bones["{joint}"].{prop_name}'
      7. Append an FCurveData with the normalized path, axis index,
         and a list of KeyframePoint objects.

    Returns all FCurveData objects found across all joints.

    Hint: CHANNEL_MAP values are tuples of (prop_name, axis_index).
    Hint: cmds.listConnections and cmds.keyframe return None when
          nothing is found — use `or []` to handle this safely.
    """
    fcurves = []

    for joint in joints:
        for maya_attr, (prop_name, axis_index) in CHANNEL_MAP.items():
            full_attr = f"{joint}.{maya_attr}"

            # Check if this attribute has an animCurve node connected
            curves = cmds.listConnections(full_attr, type="animCurve") or []
            if not curves:
                continue

            # Read keyframe times and values
            times = cmds.keyframe(full_attr, query=True, timeChange=True) or []
            values = cmds.keyframe(full_attr, query=True, valueChange=True) or []

            if not times:
                continue

            keyframes = [KeyframePoint(frame=t, value=v) for v, t in zip(values, times)]

            normalized_path = f'pose.bones["{joint}"].{prop_name}'

            fcurves.append(
                FCurveData(
                    data_path=normalized_path,
                    array_index=axis_index,
                    keyframes=keyframes,
                )
            )

    return fcurves


def _get_frame_range() -> tuple[int, int]:
    """
    Returns the current playback frame range as (start, end).

    Hint: cmds.playbackOptions with query=True and minTime=True
    returns the start frame. maxTime=True returns the end frame.
    Cast both to int before returning.
    """
    start = int(cmds.playbackOptions(query=True, minTime=True))
    end = int(cmds.playbackOptions(query=True, maxTime=True))
    return start, end


def _get_fps() -> int:
    """
    Returns the scene frame rate as an integer.

    Maya stores time units as strings. Map them to integers using
    the dictionary below, defaulting to 30 if the unit is unknown.

    Hint: cmds.currentUnit with query=True and time=True returns
    the current time unit string e.g. "ntsc".
    """
    time_unit_map = {
        "game": 15,
        "film": 24,
        "pal": 25,
        "ntsc": 30,
        "show": 48,
        "palf": 50,
        "ntscf": 60,
    }

    unit = cmds.currentUnit(query=True, time=True)
    return time_unit_map.get(unit, 30)
