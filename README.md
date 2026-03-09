# Maya Animation Validator

[Full Blog Post](https://www.justinnappi.com/project/maya-animation-gateway)

A Maya animation validation and FBX export tool built for game production pipelines. Validates joint hierarchies and animation curves against configurable pipeline rules before enforcing canonical export settings — blocking bad assets from reaching the engine before they cause problems.

---

## Overview

Animation pipelines break in predictable ways. Scale keyframes on the root bone corrupt Unreal's import. Looping animations that don't close cleanly create visible snaps in gameplay. Bone names that drift from the canonical skeleton silently discard animation data on import. This tool catches those failures at the source — inside the DCC — before the file reaches version control.

The architecture separates Maya-specific code from validation logic so the same validators can run in a headless CI environment, a different DCC tool, or a REST API without modification. The only file that imports `maya.cmds` is the adapter. Everything else is pure Python.

---

## Features

- Validates animation against configurable pipeline rules before allowing export
- Enforces canonical FBX export settings programmatically — artists cannot bypass them through the export dialog
- Blocks export on error-severity failures; logs warnings without blocking
- Structured output to Maya's Script Editor with per-rule failure context
- Pure Python validation core — no Maya required to run tests or use validators in CI
- Extensible validator architecture — adding a new rule requires a single new file

---

## Project Structure

```
maya_validator/
├── core/
│   ├── schema.py               # SceneData, FCurveData, BoneData, ValidationResult
│   ├── runner.py               # ValidationRunner — executes validators, collects results
│   └── validators/
│       ├── base.py             # Abstract Validator base class
│       ├── root_scale.py       # Checks root bone has no scale animation
│       ├── loop_clean.py       # Checks first and last frames match within tolerance
│       └── naming.py           # Checks bone names match studio convention
├── adapters/
│   └── maya_adapter.py         # Only file that imports maya.cmds
├── exporter/
│   └── maya_exporter.py        # Validates then exports FBX with enforced settings
├── shelf/
│   └── validate_and_export.py  # Maya shelf button script
└── tests/
    └── test_validators.py      # Full test suite — runs without Maya installed
```

---

## Architecture

The project is built around a single architectural seam: the `SceneData` dataclass.

```
Maya Scene
    ↓
maya_adapter.py        ← only file that imports maya.cmds
    ↓ produces
SceneData              ← tool-agnostic from here down
    ↓
ValidationRunner
    ↓ runs each
Validator              ← pure Python, no DCC dependency
    ↓ returns
list[ValidationResult]
    ↓
maya_exporter.py       ← blocks or exports based on results
```

The adapter reads Maya's dependency graph using `cmds.listConnections` to find animation curve nodes and `cmds.keyframe` to read their data. It normalizes Maya's internal attribute naming convention (`root.translateX`) into the pipeline's standard `data_path` format (`pose.bones["root"].location`) before producing `SceneData`. Validators downstream never see Maya-specific identifiers.

This means the same `RootScaleValidator`, `LoopCleanValidator`, and `NamingConventionValidator` that run from the Maya shelf button can run in a CI pipeline against exported FBX files, or be extended to support Blender or MotionBuilder by writing a new adapter with no changes to the validation core.

---

## Validators

### `RootScaleValidator`

Checks that the root bone has no scale animation curves.

Unreal Engine's FBX importer treats any scale animation on the root bone as intentional scale animation. Even constant `scale=1.0` keyframes cause incorrect scale to be applied to the character on import. The presence of the scale track is the problem, not its value.

**Severity:** Error — blocks export

```python
RootScaleValidator(root_bone_name="root")
```

---

### `LoopCleanValidator`

Checks that the animation's first and last frames match within a configurable tolerance.

Unreal plays looping `AnimSequence` assets continuously. If a bone's value at `frame_start` differs from its value at `frame_end` by more than the tolerance, the character will visibly snap or pop at the loop point during gameplay. Root bone location is excluded by default to support root motion animations.

**Severity:** Warning — logged but does not block export

```python
LoopCleanValidator(tolerance=1e-4, exclude_paths=['pose.bones["root"].location'])
```

---

### `NamingConventionValidator`

Checks that all bone names conform to a configurable regex pattern.

Unreal maps incoming FBX bones to the target `Skeleton` asset by exact string match. A bone named `Hand_L` in the FBX and `hand_l` in the Skeleton are treated as completely different bones — the animation for `Hand_L` is silently discarded. The default pattern enforces `lowercase_with_underscores` convention.

**Severity:** Error — blocks export

```python
NamingConventionValidator(pattern=r"^[a-z][a-z0-9_]*$")
```

---

## Installation

**Requirements:** Python 3.10+, Maya (any recent version with Python 3)

Clone the repository:

```bash
git clone https://github.com/yourusername/maya-validator.git
cd maya-validator
```

Install test dependencies:

```bash
pip install pytest
```

Run the test suite (no Maya required):

```bash
pytest tests/ -v
```

---

## Usage

### Running from the Maya Shelf

1. Open Maya's Script Editor (`Windows > General Editors > Script Editor`)
2. Create a new Python tab
3. Open `shelf/validate_and_export.py` and update `PROJECT_ROOT` to your local project path
4. Paste the full script into the tab
5. Select all text (`Ctrl+A`) and middle-mouse drag it onto your shelf
6. Select the root joint of your skeleton in the viewport
7. Click the shelf button

A file dialog will appear if validation passes. If errors are found, export is blocked and the Script Editor output shows which rules failed and why.

### Running Validation Manually

```python
import sys
sys.path.insert(0, "/path/to/maya_validator")

from adapters.maya_adapter import extract_scene_data
from core.validators.root_scale import RootScaleValidator
from core.validators.loop_clean import LoopCleanValidator
from core.validators.naming import NamingConventionValidator
from core.runner import ValidationRunner

scene = extract_scene_data("root")

runner = ValidationRunner([
    RootScaleValidator(),
    LoopCleanValidator(),
    NamingConventionValidator(),
])

results = runner.run(scene)

for r in results:
    icon = "✓" if r.status == "pass" else "✗"
    print(f"{icon} [{r.severity}] {r.rule_name}: {r.message}")
```

### Adding a Custom Validator

Create a new file in `core/validators/`. Inherit from `Validator`, implement `rule_name` and `run()`. Add it to the runner. No other files change.

```python
# core/validators/frame_rate.py
from core.validators.base import Validator
from core.schema import SceneData, ValidationResult

class FrameRateValidator(Validator):
    def __init__(self, required_fps: int = 30):
        self.required_fps = required_fps

    @property
    def rule_name(self) -> str:
        return "frame_rate_check"

    def run(self, scene: SceneData) -> ValidationResult:
        if scene.fps != self.required_fps:
            return ValidationResult(
                rule_name=self.rule_name,
                status="fail",
                severity="error",
                message=f"Scene is {scene.fps}fps — pipeline requires {self.required_fps}fps",
                context={"scene_fps": scene.fps, "required_fps": self.required_fps}
            )
        return ValidationResult(self.rule_name, "pass", "error", f"Frame rate is {self.required_fps}fps", {})
```

---

## Running Tests

The full test suite runs without Maya installed. Tests cover all three validators and the runner, including edge cases like constant-value scale curves, root motion exclusion, tolerance boundaries, and validator exception handling.

```bash
pytest tests/ -v

# Expected output
tests/test_validators.py::TestRootScaleValidator::test_passes_with_no_fcurves PASSED
tests/test_validators.py::TestRootScaleValidator::test_fails_with_scale_keyframe_on_root PASSED
tests/test_validators.py::TestLoopCleanValidator::test_excludes_root_location_by_default PASSED
...
24 passed in 0.14s
```

---

## Background

This project started as a Blender validation addon and was ported to Maya after signals from a technical interview process indicated Maya was the primary DCC in the target pipeline. The port took approximately three days and required writing only the adapter layer — the validation core transferred without modification. That outcome was the point of the architecture.

The broader pipeline design this tool fits into — including CI validation, pre-commit hooks, a FastAPI REST layer, and Unreal Engine import automation — is documented in the project wiki.

---

## License

MIT
