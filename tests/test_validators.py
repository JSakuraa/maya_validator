# tests/test_validators.py
import sys
import os

from core.validators.base import Validator

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.schema import SceneData, BoneData, FCurveData, KeyframePoint, ValidationResult
from core.validators.root_scale import RootScaleValidator
from core.validators.loop_clean import LoopCleanValidator
from core.validators.naming import NamingConventionValidator
from core.runner import ValidationRunner


# ─── Helpers ────────────────────────────────────────────────────────────────


def make_scene(**kwargs) -> SceneData:
    """Creates a minimal valid SceneData for testing."""
    defaults = dict(
        bones=[
            BoneData(name="root", parent=None),
            BoneData(name="pelvis", parent="root"),
            BoneData(name="spine_01", parent="pelvis"),
        ],
        fcurves=[],
        frame_start=1,
        frame_end=60,
        asset_name="test_walk",
        source_tool="maya",
        fps=30,
    )
    defaults.update(kwargs)
    return SceneData(**defaults)  # pyright: ignore[reportArgumentType]


def make_fcurve(bone: str, prop: str, axis: int, keys: list[tuple]) -> FCurveData:
    """Creates an FCurveData with the given keyframes."""
    return FCurveData(
        data_path=f'pose.bones["{bone}"].{prop}',
        array_index=axis,
        keyframes=[KeyframePoint(frame=f, value=v) for f, v in keys],
    )


# ─── RootScaleValidator ──────────────────────────────────────────────────────


class TestRootScaleValidator:
    def test_passes_with_no_fcurves(self):
        scene = make_scene()
        result = RootScaleValidator().run(scene)
        assert result.status == "pass"
        assert result.severity == "error"

    def test_passes_with_location_curves_only(self):
        fc = make_fcurve("root", "location", 0, [(1, 0.0), (60, 1.0)])
        scene = make_scene(fcurves=[fc])
        result = RootScaleValidator().run(scene)
        assert result.status == "pass"

    def test_fails_with_scale_keyframe_on_root(self):
        fc = make_fcurve("root", "scale", 0, [(1, 1.0)])
        scene = make_scene(fcurves=[fc])
        result = RootScaleValidator().run(scene)
        assert result.status == "fail"
        assert result.severity == "error"
        assert "root" in result.context["bone"]
        assert 1 in result.context["frames"]

    def test_fails_even_with_constant_1_scale(self):
        """Even scale=1.0 on root is an error — the track existing is the problem."""
        fc = make_fcurve("root", "scale", 0, [(1, 1.0), (30, 1.0), (60, 1.0)])
        scene = make_scene(fcurves=[fc])
        result = RootScaleValidator().run(scene)
        assert result.status == "fail"

    def test_passes_scale_on_non_root_bone(self):
        """Scale curves on non-root bones are not checked by this validator."""
        fc = make_fcurve("pelvis", "scale", 0, [(1, 1.0)])
        scene = make_scene(fcurves=[fc])
        result = RootScaleValidator().run(scene)
        assert result.status == "pass"

    def test_custom_root_bone_name(self):
        fc = make_fcurve("hips", "scale", 0, [(1, 1.0)])
        scene = make_scene(fcurves=[fc])
        result = RootScaleValidator(root_bone_name="hips").run(scene)
        assert result.status == "fail"


# ─── LoopCleanValidator ──────────────────────────────────────────────────────


class TestLoopCleanValidator:
    def test_passes_with_no_fcurves(self):
        scene = make_scene()
        result = LoopCleanValidator().run(scene)
        assert result.status == "pass"

    def test_passes_matching_first_and_last_frame(self):
        fc = make_fcurve("pelvis", "location", 1, [(1, 0.0), (60, 0.0)])
        scene = make_scene(fcurves=[fc])
        result = LoopCleanValidator().run(scene)
        assert result.status == "pass"

    def test_fails_drifting_value(self):
        fc = make_fcurve("pelvis", "location", 1, [(1, 0.0), (60, 0.5)])
        scene = make_scene(fcurves=[fc])
        result = LoopCleanValidator().run(scene)
        assert result.status == "fail"
        assert result.severity == "warning"
        assert len(result.context["mismatches"]) == 1

    def test_excludes_root_location_by_default(self):
        """Root motion clip — root travels, should not be flagged."""
        fc = make_fcurve("root", "location", 0, [(1, 0.0), (60, 5.0)])
        scene = make_scene(fcurves=[fc])
        result = LoopCleanValidator().run(scene)
        assert result.status == "pass"

    def test_respects_tolerance(self):
        """Delta of 0.0001 should pass with default tolerance of 1e-4."""
        fc = make_fcurve("spine_01", "rotation_euler", 1, [(1, 0.0), (60, 0.00009)])
        scene = make_scene(fcurves=[fc])
        result = LoopCleanValidator(tolerance=1e-4).run(scene)
        assert result.status == "pass"

    def test_fails_above_tolerance(self):
        fc = make_fcurve("spine_01", "rotation_euler", 1, [(1, 0.0), (60, 0.001)])
        scene = make_scene(fcurves=[fc])
        result = LoopCleanValidator(tolerance=1e-4).run(scene)
        assert result.status == "fail"

    def test_multiple_failing_curves_all_reported(self):
        fc1 = make_fcurve("pelvis", "location", 0, [(1, 0.0), (60, 1.0)])
        fc2 = make_fcurve("spine_01", "rotation_euler", 1, [(1, 0.0), (60, 0.5)])
        scene = make_scene(fcurves=[fc1, fc2])
        result = LoopCleanValidator().run(scene)
        assert result.status == "fail"
        assert len(result.context["mismatches"]) == 2


# ─── NamingConventionValidator ───────────────────────────────────────────────


class TestNamingConventionValidator:
    def test_passes_valid_lowercase_names(self):
        scene = make_scene()  # default bones are already valid
        result = NamingConventionValidator().run(scene)
        assert result.status == "pass"

    def test_fails_uppercase_first_letter(self):
        scene = make_scene(bones=[BoneData("Root", None), BoneData("pelvis", "Root")])
        result = NamingConventionValidator().run(scene)
        assert result.status == "fail"
        assert "Root" in result.context["violations"]

    def test_fails_camel_case(self):
        scene = make_scene(bones=[BoneData("root", None), BoneData("leftFoot", "root")])
        result = NamingConventionValidator().run(scene)
        assert result.status == "fail"
        assert "leftFoot" in result.context["violations"]

    def test_fails_blender_default_naming(self):
        """Blender names like 'Bone.001' should fail."""
        scene = make_scene(bones=[BoneData("root", None), BoneData("Bone.001", "root")])
        result = NamingConventionValidator().run(scene)
        assert result.status == "fail"

    def test_passes_names_with_numbers_and_underscores(self):
        scene = make_scene(
            bones=[
                BoneData("root", None),
                BoneData("spine_01", "root"),
                BoneData("hand_l", "root"),
                BoneData("thigh_twist_01", "root"),
            ]
        )
        result = NamingConventionValidator().run(scene)
        assert result.status == "pass"

    def test_fails_name_starting_with_number(self):
        scene = make_scene(bones=[BoneData("root", None), BoneData("1spine", "root")])
        result = NamingConventionValidator().run(scene)
        assert result.status == "fail"

    def test_multiple_violations_all_reported(self):
        scene = make_scene(
            bones=[
                BoneData("Root", None),
                BoneData("Pelvis", "Root"),
                BoneData("SPINE", "Pelvis"),
            ]
        )
        result = NamingConventionValidator().run(scene)
        assert result.status == "fail"
        assert len(result.context["violations"]) == 3


# ─── ValidationRunner ────────────────────────────────────────────────────────


class TestValidationRunner:
    def test_runs_all_validators(self):
        scene = make_scene()
        validators = [
            RootScaleValidator(),
            LoopCleanValidator(),
            NamingConventionValidator(),
        ]
        runner = ValidationRunner(validators)
        results = runner.run(scene)
        assert len(results) == 3

    def test_has_errors_returns_true_when_error_fails(self):
        fc = make_fcurve("root", "scale", 0, [(1, 1.0)])
        scene = make_scene(fcurves=[fc])
        runner = ValidationRunner([RootScaleValidator()])
        results = runner.run(scene)
        assert runner.has_errors(results) is True

    def test_has_errors_returns_false_when_only_warnings(self):
        fc = make_fcurve("pelvis", "location", 1, [(1, 0.0), (60, 0.5)])
        scene = make_scene(fcurves=[fc])
        runner = ValidationRunner([LoopCleanValidator()])
        results = runner.run(scene)
        assert runner.has_errors(results) is False
        assert runner.has_warnings(results) is True

    def test_runner_catches_validator_exception(self):
        """A crashing validator should not crash the runner."""

        class BrokenValidator(Validator):
            @property
            def rule_name(self):
                return "broken"

            def run(self, scene):
                raise RuntimeError("simulated crash")

        scene = make_scene()
        runner = ValidationRunner([BrokenValidator()])
        results = runner.run(scene)
        assert len(results) == 1
        assert results[0].status == "fail"
        assert "exception" in results[0].context
