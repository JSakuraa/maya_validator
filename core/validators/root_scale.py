from core.validators.base import Validator
from core.schema import SceneData, ValidationResult


class RootScaleValidator(Validator):
    """
    Checks that the root bone has no scale animation curves.

    Why this matters:
    Unreal Engine's FBX importer treats any scale animation data on the
    root bone as intentional scale animation. Even constant scale=1.0
    keyframes cause incorrect scale to be applied to the character.
    The presence of the scale track is the problem, not its value.

    What to check:
    Scan scene.fcurves for any curve whose data_path matches the root
    bone's scale property AND has at least one keyframe.
    If found, return a fail result with severity "error".
    """

    def __init__(self, root_bone_name: str = "root"):
        """
        root_bone_name: name of the root bone to check.
                        Default "root". Override for rigs that use
                        a different root bone name e.g. "hips".
        """
        self.root_bone_name = root_bone_name

    @property
    def rule_name(self) -> str:
        return "root_scale_validator"

    def run(self, scene: SceneData) -> ValidationResult:
        """
        Scan scene.fcurves for scale keyframes on the root bone.

        The expected data_path for root scale curves is:
            'pose.bones["<root_bone_name>"].scale'

        Return fail with severity "error" if any are found.
        Include the bone name and offending frame numbers in context.
        """
        # TODO: implement root scale detection
        expected_path = f'pose.bones["{self.root_bone_name}"].scale'

        violations = [
            fc
            for fc in scene.fcurves
            if fc.data_path == expected_path and len(fc.keyframes) > 0
        ]

        if violations:
            offending_frames = [kp.frame for fc in violations for kp in fc.keyframes]
            return ValidationResult(
                rule_name=self.rule_name,
                status="fail",
                severity="error",
                message=f"Root bone '{self.root_bone_name}' has scale animation. "
                "This will cause incorrect scaling in Unreal Engine.",
                context={"bone": self.root_bone_name, "frames": offending_frames},
            )

        return ValidationResult(
            rule_name=self.rule_name,
            status="pass",
            severity="error",
            message=f"Root bone '{self.root_bone_name}' has no scale animation.",
            context={},
        )
