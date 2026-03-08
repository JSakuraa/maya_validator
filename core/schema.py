from dataclasses import dataclass, field


@dataclass
class KeyframePoint:
    """
    One keyframe on one animation curve.
    frame: timeline position (e.g. 1.0, 12.0, 24.0)
    value: property value at that frame
    """

    frame: float
    value: float


@dataclass
class FCurveData:
    """
    One animation curve for one scalar channel on one bone.

    data_path:   normalized identifier for the bone and property.
                 Format: 'pose.bones["bone_name"].property'
                 e.g.    'pose.bones["root"].location'

    array_index: which axis this curve animates. 0=X, 1=Y, 2=Z

    keyframes:   ordered list of KeyframePoint objects.
    """

    data_path: str
    array_index: int
    keyframes: list[KeyframePoint] = field(default_factory=list)

    def evaluate(self, frame: float) -> float:
        """
        Returns the interpolated value at the given frame.
        Uses linear interpolation between surrounding keyframes.
        Returns 0.0 if no keyframes exist.
        Clamps to first/last value if frame is out of range.
        """
        # TODO: implement linear interpolation across self.keyframes
        if not self.keyframes:
            return 0.0

        sorted_keyframes = sorted(self.keyframes, key=lambda k: k.frame)

        if frame <= sorted_keyframes[0].frame:
            return sorted_keyframes[0].value

        if frame >= sorted_keyframes[-1].frame:
            return sorted_keyframes[-1].value

        for i in range(len(sorted_keyframes) - 1):
            kf1 = sorted_keyframes[i]
            kf2 = sorted_keyframes[i + 1]
            if kf1.frame < frame < kf2.frame:
                t = (frame - kf1.frame) / (kf2.frame - kf1.frame)
                return kf1.value + t * (kf2.value - kf1.value)

        return sorted_keyframes[-1].value


@dataclass
class BoneData:
    """
    One bone in the skeleton hierarchy.
    name:   the bone's name (e.g. "root", "spine_01", "hand_l")
    parent: parent bone name, or None if this is the root bone
    """

    name: str
    parent: str | None


@dataclass
class SceneData:
    """
    A complete, tool-agnostic representation of one animation asset.
    Produced by an adapter. Consumed by validators.

    bones:       the full skeleton hierarchy
    fcurves:     all animated channels in the scene
    frame_start: first frame of the animation range
    frame_end:   last frame of the animation range
    asset_name:  name of the asset
    source_tool: which DCC produced this — "maya", "blender", "motionbuilder"
    fps:         frame rate of the scene
    """

    bones: list[BoneData]
    fcurves: list[FCurveData]
    frame_start: int
    frame_end: int
    asset_name: str
    source_tool: str
    fps: int = 30


@dataclass
class ValidationResult:
    """
    The result of one validator running against one SceneData.

    rule_name: identifier for the rule that produced this result
    status:    "pass" or "fail"
    severity:  "error" (blocks export) or "warning" (does not block)
    message:   human-readable explanation
    context:   structured data about the failure for debugging
    """

    rule_name: str
    status: str
    severity: str
    message: str
    context: dict = field(default_factory=dict)
