from core.validators.base import Validator
from core.schema import SceneData, ValidationResult


class LoopCleanValidator(Validator):
    """
    Checks that a looping animation's first and last frames match.

    Why this matters:
    Unreal plays looping AnimSequences continuously. If a bone's value
    at frame_start differs from its value at frame_end by more than the
    tolerance, the character will visibly snap at the loop point.

    What to check:
    For each FCurve not in exclude_paths, evaluate the value at
    scene.frame_start and scene.frame_end using fc.evaluate().
    If abs(start_val - end_val) > tolerance, the curve fails.

    Root location is excluded by default because root motion animations
    are expected to travel — their start and end positions differ
    intentionally.
    """

    def __init__(self, tolerance: float = 1e-4, exclude_paths: list[str] = []):
        """
        tolerance:     maximum acceptable delta between first and last frame.
        exclude_paths: list of data_paths to skip entirely.
                       Defaults to excluding root bone location.
        """
        # Hint: exclude_paths default should be ['pose.bones["root"].location']
        #       Set this in the body, not in the signature, to avoid
        #       the mutable default argument Python gotcha.
        self.tolerance = tolerance
        self.exclude_paths = exclude_paths or ['pose.bones["root"].location']

    @property
    def rule_name(self) -> str:
        return "loop_clean_check"

    def run(self, scene: SceneData) -> ValidationResult:
        """
        Check every FCurve not in exclude_paths for loop cleanliness.

        For each FCurve:
          1. Skip if data_path is in self.exclude_paths
          2. Evaluate the value at scene.frame_start
          3. Evaluate the value at scene.frame_end
          4. If abs(start - end) > self.tolerance, record a mismatch

        Return fail with severity "warning" if any mismatches found.
        Include the list of mismatch dicts in context under key "mismatches".
        Each mismatch dict should contain: data_path, array_index, delta.
        """
        # TODO: implement loop cleanliness check
        mismatches = []

        for fc in scene.fcurves:
            if fc.data_path in self.exclude_paths:
                continue

            start_val = fc.evaluate(scene.frame_start)
            end_val = fc.evaluate(scene.frame_end)
            delta = abs(start_val - end_val)

            if delta > self.tolerance:
                mismatches.append(
                    {
                        "data_path": fc.data_path,
                        "arraay_index": fc.array_index,
                        "delta": round(delta, 6),
                        "start_val": round(start_val, 6),
                        "end_val": round(end_val, 6),
                    }
                )

        if mismatches:
            return ValidationResult(
                rule_name=self.rule_name,
                status="fail",
                severity="warning",
                message=f"{len(mismatches)} curve(s) do not loop cleanly. "
                f"Character will snap at loop point.",
                context={"mismatches": mismatches},
            )

        return ValidationResult(
            rule_name=self.rule_name,
            status="pass",
            severity="warning",
            message="All loops cleanly within tolerance.",
            context={},
        )
