"""Schema and trajectory validation.

Validates primitives, composed sequences, and skill library structures
to ensure data integrity across the pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Schema definitions
# ---------------------------------------------------------------------------

PRIMITIVE_SCHEMA = {
    "required": {"type", "start", "end"},
    "optional": {"confidence", "description", "metadata", "trajectory"},
    "types": {
        "type": str,
        "start": int,
        "end": int,
        "confidence": (int, float),
        "description": str,
        "metadata": dict,
    },
}

VALID_PRIMITIVE_TYPES = {"reach", "grasp", "lift", "transport", "place"}


# ---------------------------------------------------------------------------
# Primitive validation
# ---------------------------------------------------------------------------


def validate_primitive(primitive: dict[str, Any]) -> list[str]:
    """Validate a single primitive dict against the schema.

    Args:
        primitive: Dict representing a skill primitive.

    Returns:
        List of error message strings. Empty list if valid.
    """
    errors: list[str] = []

    # Check required fields
    missing = PRIMITIVE_SCHEMA["required"] - set(primitive.keys())
    if missing:
        errors.append(f"Missing required fields: {sorted(missing)}")

    # Check field types
    for field, expected_type in PRIMITIVE_SCHEMA["types"].items():
        if field not in primitive:
            continue
        value = primitive[field]
        if not isinstance(value, expected_type):
            errors.append(
                f"Field '{field}' has wrong type: expected {expected_type.__name__}, "
                f"got {type(value).__name__}"
            )

    # Check primitive type is known
    ptype = primitive.get("type")
    if ptype is not None and ptype not in VALID_PRIMITIVE_TYPES:
        errors.append(
            f"Unknown primitive type '{ptype}'. " f"Valid types: {sorted(VALID_PRIMITIVE_TYPES)}"
        )

    # Check frame range validity
    start = primitive.get("start")
    end = primitive.get("end")
    if start is not None and end is not None:
        if not isinstance(start, int) or not isinstance(end, int):
            pass  # Already caught above
        else:
            if start < 0:
                errors.append(f"Start frame {start} is negative")
            if end < 0:
                errors.append(f"End frame {end} is negative")
            if start >= end:
                errors.append(f"Invalid frame range: start ({start}) >= end ({end})")

    # Check confidence bounds
    confidence = primitive.get("confidence")
    if confidence is not None:
        if not isinstance(confidence, (int, float)):
            pass  # Already caught above
        else:
            if not 0.0 <= confidence <= 1.0:
                errors.append(f"Confidence {confidence} is outside [0.0, 1.0]")

    return errors


def is_valid_primitive(primitive: dict[str, Any]) -> bool:
    """Quick check: is this primitive valid?

    Args:
        primitive: Dict representing a skill primitive.

    Returns:
        True if valid, False otherwise.
    """
    return len(validate_primitive(primitive)) == 0


# ---------------------------------------------------------------------------
# Sequence validation
# ---------------------------------------------------------------------------


def validate_sequence(sequence: list[dict[str, Any]]) -> list[str]:
    """Validate a composed sequence of primitives.

    Checks for:
    - Empty sequences
    - Invalid individual primitives
    - Temporal ordering (start times should be non-decreasing)
    - Logical flow (grasp before lift, lift before place, etc.)
    - Overlapping segments of different types

    Args:
        sequence: List of primitive dicts.

    Returns:
        List of error message strings. Empty list if valid.
    """
    errors: list[str] = []

    if not sequence:
        errors.append("Sequence is empty")
        return errors

    # Validate each primitive individually
    for i, primitive in enumerate(sequence):
        primitive_errors = validate_primitive(primitive)
        for err in primitive_errors:
            errors.append(f"Primitive {i}: {err}")

    # If individual primitives are invalid, skip sequence-level checks
    if errors:
        return errors

    # Check temporal ordering: start times should be non-decreasing
    starts = [p["start"] for p in sequence]
    for i in range(1, len(starts)):
        if starts[i] < starts[i - 1]:
            errors.append(
                f"Temporal ordering violated at position {i}: "
                f"start {starts[i]} < previous start {starts[i - 1]}"
            )

    # Check for overlapping segments of different types
    for i in range(len(sequence)):
        for j in range(i + 1, len(sequence)):
            a = sequence[i]
            b = sequence[j]
            # Overlap if a starts before b ends and a ends after b starts
            if a["start"] < b["end"] and a["end"] > b["start"]:
                if a["type"] != b["type"]:
                    errors.append(
                        f"Overlapping segments of different types: "
                        f"{a['type']} ({a['start']}-{a['end']}) and "
                        f"{b['type']} ({b['start']}-{b['end']})"
                    )

    # Check logical flow constraints
    type_order = [p["type"] for p in sequence]

    # Lift should follow grasp
    for i, ptype in enumerate(type_order):
        if ptype == "lift":
            preceding = type_order[:i]
            if "grasp" not in preceding:
                errors.append(f"Lift at position {i} has no preceding grasp in sequence")

    # Place should follow lift (or transport)
    for i, ptype in enumerate(type_order):
        if ptype == "place":
            preceding = type_order[:i]
            if "lift" not in preceding and "transport" not in preceding:
                errors.append(f"Place at position {i} has no preceding lift or transport")

    # Transport should follow lift
    for i, ptype in enumerate(type_order):
        if ptype == "transport":
            preceding = type_order[:i]
            if "lift" not in preceding:
                errors.append(f"Transport at position {i} has no preceding lift")

    return errors


def is_valid_sequence(sequence: list[dict[str, Any]]) -> bool:
    """Quick check: is this sequence valid?

    Args:
        sequence: List of primitive dicts.

    Returns:
        True if valid, False otherwise.
    """
    return len(validate_sequence(sequence)) == 0


# ---------------------------------------------------------------------------
# Skill library validation
# ---------------------------------------------------------------------------


def validate_skill_library(path: str) -> list[str]:
    """Validate a skill library directory structure.

    Checks for:
    - Directory exists
    - Expected subdirectories for each primitive type
    - At least one metadata.yaml per subdirectory
    - Valid metadata.yaml structure

    Args:
        path: Root directory of the skill library.

    Returns:
        List of error message strings. Empty list if valid.
    """
    errors: list[str] = []
    lib_path = Path(path)

    if not lib_path.exists():
        errors.append(f"Library path does not exist: {path}")
        return errors

    if not lib_path.is_dir():
        errors.append(f"Library path is not a directory: {path}")
        return errors

    # Check for expected primitive type subdirectories
    for ptype in VALID_PRIMITIVE_TYPES:
        type_dir = lib_path / ptype
        if not type_dir.exists():
            # Not an error — some types may not have data yet
            continue

        if not type_dir.is_dir():
            errors.append(f"Expected directory, found file: {type_dir}")
            continue

        # Check for at least one metadata.yaml
        meta_files = list(type_dir.rglob("metadata.yaml"))
        if not meta_files:
            errors.append(f"No metadata.yaml files found in {type_dir}")
            continue

        # Validate each metadata.yaml
        for meta_file in meta_files:
            try:
                import yaml

                metadata = yaml.safe_load(meta_file.read_text()) or {}
            except Exception as e:
                errors.append(f"Failed to parse {meta_file}: {e}")
                continue

            if "description" not in metadata:
                errors.append(f"Missing 'description' in {meta_file}")

    return errors


def is_valid_skill_library(path: str) -> bool:
    """Quick check: is this skill library valid?

    Args:
        path: Root directory of the skill library.

    Returns:
        True if valid, False otherwise.
    """
    return len(validate_skill_library(path)) == 0


# ---------------------------------------------------------------------------
# Trajectory validation
# ---------------------------------------------------------------------------


def validate_trajectory(trajectory: dict[str, Any]) -> list[str]:
    """Validate a robot trajectory dict.

    Checks for:
    - Required keys (actions, states or observations)
    - Array length consistency
    - Non-empty trajectory

    Args:
        trajectory: Dict with trajectory data.

    Returns:
        List of error message strings. Empty list if valid.
    """
    errors: list[str] = []

    if not trajectory:
        errors.append("Trajectory is empty")
        return errors

    # Check for at least one data key
    data_keys = ["actions", "states", "observations", "state"]
    found_keys = [k for k in data_keys if k in trajectory]
    if not found_keys:
        errors.append(f"Trajectory missing data keys. Expected one of: {data_keys}")
        return errors

    # Check length consistency across arrays
    lengths = []
    for key in found_keys:
        value = trajectory[key]
        if hasattr(value, "__len__"):
            lengths.append((key, len(value)))

    if len(lengths) > 1:
        first_key, first_len = lengths[0]
        for key, length in lengths[1:]:
            if length != first_len:
                errors.append(
                    f"Length mismatch: {first_key} has {first_len} frames, "
                    f"{key} has {length} frames"
                )

    # Check trajectory is not empty
    if lengths and lengths[0][1] == 0:
        errors.append("Trajectory has zero frames")

    return errors


def is_valid_trajectory(trajectory: dict[str, Any]) -> bool:
    """Quick check: is this trajectory valid?

    Args:
        trajectory: Dict with trajectory data.

    Returns:
        True if valid, False otherwise.
    """
    return len(validate_trajectory(trajectory)) == 0
