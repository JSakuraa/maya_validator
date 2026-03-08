import re
from core.validators.base import Validator
from core.schema import SceneData, ValidationResult


class NamingConventionValidator(Validator):
    """
    Checks that all bone names conform to the studio naming convention.

    Why this matters:
    Unreal maps incoming FBX bones to the target Skeleton asset by
    exact string match. A bone named 'Hand_L' in the FBX and 'hand_l'
    in the Skeleton are treated as different bones — the animation for
    'Hand_L' is silently discarded on import.

    What to check:
    Every bone name in scene.bones must match the configured regex
    pattern. The default pattern requires: lowercase letters, numbers,
    and underscores only, starting with a lowercase letter.

    Valid:   root, spine_01, hand_l, thigh_twist_01
    Invalid: Root, Hand_L, Bone.001, leftFoot, 1spine
    """

    def __init__(self, pattern: str = r"^[a-z][a-z0-9_]*$"):
        """
        pattern: regex pattern bone names must match.
                Default enforces lowercase_with_underscores convention.
        """
        # TODO: compile the pattern and store as an instance variable
        self.pattern = re.compile(pattern)

    @property
    def rule_name(self) -> str:
        # TODO: return the string identifier for this rule
        return "naming_convention_check"

    def run(self, scene: SceneData) -> ValidationResult:
        """
        Test every bone name in scene.bones against self.pattern.

        Collect all names that do not match into a violations list.
        Return fail with severity "error" if violations exist.
        Include the violations list in context under key "violations".
        """
        # TODO: implement naming convention check
        violations = [
            bone.name for bone in scene.bones if not self.pattern.match(bone.name)
        ]

        if violations:
            return ValidationResult(
                rule_name=self.rule_name,
                status="fail",
                severity="error",
                message=f"{len(violations)} bone(s) violate the naming convention. "
                f"Pattern required: {self.pattern.pattern}",
                context={"violations": violations},
            )

        return ValidationResult(
            rule_name=self.rule_name,
            status="pass",
            severity="",
            message="All bone names conform to the naming convention.",
            context={},
        )
