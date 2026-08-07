"""Auto-discover and register all primitive classes.

Provides a central registry for looking up primitive detectors by name.
Adding a new primitive is as simple as creating a new subclass of Primitive
and importing it here.
"""

from __future__ import annotations

from typing import Type

from skill_primitives.primitives.base import Primitive
from skill_primitives.primitives.reach import Reach
from skill_primitives.primitives.grasp import Grasp
from skill_primitives.primitives.lift import Lift
from skill_primitives.primitives.transport import Transport
from skill_primitives.primitives.place import Place

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_PRIMITIVES: dict[str, Type[Primitive]] = {
    cls.name: cls
    for cls in [Reach, Grasp, Lift, Transport, Place]
    if cls.name
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_primitive(name: str) -> Type[Primitive]:
    """Retrieve a primitive class by name.

    Args:
        name: Primitive type name (e.g., "grasp", "lift").

    Returns:
        The Primitive subclass.

    Raises:
        KeyError: If the primitive name is not registered.
    """
    if name not in _PRIMITIVES:
        available = ", ".join(sorted(_PRIMITIVES.keys()))
        raise KeyError(
            f"Unknown primitive: '{name}'. "
            f"Available primitives: {available}"
        )
    return _PRIMITIVES[name]


def list_primitives() -> list[str]:
    """Return a list of all registered primitive names.

    Returns:
        Sorted list of primitive type names.
    """
    return sorted(_PRIMITIVES.keys())


def get_all_primitives() -> dict[str, Type[Primitive]]:
    """Return the full registry mapping.

    Returns:
        Dict mapping primitive names to their classes.
    """
    return dict(_PRIMITIVES)


def register_primitive(cls: Type[Primitive]) -> Type[Primitive]:
    """Decorator to register a new primitive class.

    Usage:
        @register_primitive
        class MyCustomPrimitive(Primitive):
            name = "custom"
            ...

    Args:
        cls: A Primitive subclass to register.

    Returns:
        The class (for decorator chaining).
    """
    if not cls.name:
        raise ValueError(f"Primitive class {cls.__name__} must have a 'name' attribute")
    _PRIMITIVES[cls.name] = cls
    return cls


def create_detector(name: str) -> Primitive:
    """Factory: create an instance of a primitive detector.

    Args:
        name: Primitive type name.

    Returns:
        Instantiated Primitive detector.
    """
    cls = get_primitive(name)
    return cls()


def detect_all(
    gripper: Any,
    state: Any | None = None,
    velocity: Any | None = None,
) -> list[dict[str, Any]]:
    """Run all registered primitive detectors on a trajectory.

    Convenience function that runs every detector and returns
    all detected segments sorted by start frame.

    Args:
        gripper: Array of gripper states.
        state: Array of robot state observations.
        velocity: Array of end-effector velocities.

    Returns:
        List of all detected segments, sorted by start frame.
    """
    all_segments: list[dict[str, Any]] = []

    for name in list_primitives():
        detector = create_detector(name)
        segments = detector.detect(gripper, state, velocity)
        all_segments.extend(segments)

    # Sort by start frame
    all_segments.sort(key=lambda s: s["start"])
    return all_segments
