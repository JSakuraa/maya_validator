# core/validators/base.py
from abc import ABC, abstractmethod
from core.schema import SceneData, ValidationResult


class Validator(ABC):
    """
    Abstract base class for all validators.

    Every validator must implement:
    - rule_name property: a unique string identifier for this rule
    - run() method: accepts SceneData, returns ValidationResult

    Validators must not import bpy, maya.cmds, or any DCC-specific module.
    They operate exclusively on SceneData objects.
    """

    @property
    @abstractmethod
    def rule_name(self) -> str:
        """Unique identifier for this validation rule."""
        pass

    @abstractmethod
    def run(self, scene: SceneData) -> ValidationResult:
        """
        Run this validation rule against the provided scene data.
        Returns a ValidationResult with status "pass" or "fail".
        Must never raise an exception — catch errors internally and
        return a fail result with the error in the context field.
        """
        pass
