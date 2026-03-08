from core.schema import SceneData, ValidationResult
from core.validators.base import Validator


class ValidationRunner:
    """
    Executes a list of validators against a SceneData object.

    The runner does not know which specific validators it runs.
    It calls run() on everything it is given and collects results.
    Adding a new validator requires no changes to this file.
    """

    def __init__(self, validators: list[Validator]):
        """
        validators: list of Validator instances to run.
                    The runner stores these and runs them in order.
        """
        self.validators = validators

    def run(self, scene: SceneData) -> list[ValidationResult]:
        """
        Run all validators against the scene.
        Returns a list of ValidationResult objects, one per validator.

        Important: never let a single validator crash the whole run.
        Wrap each validator call in a try/except. If a validator raises
        an exception, append a fail ValidationResult with the exception
        message in context under key "exception", then continue.
        """
        results = []
        for validator in self.validators:
            try:
                res = validator.run(scene)
                results.append(res)
            except Exception as e:
                results.append(
                    ValidationResult(
                        rule_name=validator.rule_name,
                        status="fail",
                        severity="error",
                        message=f"Validator raised an unexpected exception: {e}",
                        context={"exception": str(e)},
                    )
                )
        return results

    def has_errors(self, results: list[ValidationResult]) -> bool:
        """
        Returns True if any result has status "fail" AND severity "error".
        Error-severity failures block export.
        """
        return any(r.status == "fail" and r.severity == "error" for r in results)

    def has_warnings(self, results: list[ValidationResult]) -> bool:
        """
        Returns True if any result has status "fail" AND severity "warning".
        Warning-severity failures are logged but do not block export.
        """
        return any(r.status == "fail" and r.severity == "warning" for r in results)
