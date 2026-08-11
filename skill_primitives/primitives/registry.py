"""registry.py — Central registry for skill primitive discovery.

Provides runtime lookup of concrete primitive classes by name. All
primitives are registered eagerly at import time so that the ``annotate``
script can resolve type strings (e.g. ``"grasp"``) to detector classes
without filesystem scanning.
"""

from __future__ import annotations

from skill_primitives.primitives.base import Primitive
from skill_primitives.primitives.grasp import Grasp
from skill_primitives.primitives.lift import Lift
from skill_primitives.primitives.place import Place
from skill_primitives.primitives.reach import Reach
from skill_primitives.primitives.transport import Transport

# ---------------------------------------------------------------------------

_PRIMITIVES: dict[str, type[Primitive]] = {}

# Eagerly register all imported concrete primitives
for _cls in (Grasp, Lift, Place, Reach, Transport):
    if _cls.name:
        _PRIMITIVES[_cls.name] = _cls

# ---------------------------------------------------------------------------


def get_primitive(name: str) -> type[Primitive]:
    """Retrieve a primitive class by name.

    Args:
        name: Primitive type name (e.g. ``"grasp"``, ``"lift"``).

    Returns:
        The registered primitive class.

    Raises:
        KeyError: If the primitive name is not registered.
    """
    if name not in _PRIMITIVES:
        available = ", ".join(sorted(_PRIMITIVES.keys()))
        raise KeyError(f"Unknown primitive: '{name}'. Available primitives: {available}")
    return _PRIMITIVES[name]


def list_primitives() -> list[str]:
    """Return a sorted list of all registered primitive names.

    Returns:
        Sorted list of primitive type names.
    """
    return sorted(_PRIMITIVES.keys())


def get_all_primitives() -> dict[str, type[Primitive]]:
    """Return a copy of the full primitive registry.

    Returns:
        Dict mapping primitive names to their classes.
    """
    return dict(_PRIMITIVES)


def register_primitive(cls: type[Primitive]) -> type[Primitive]:
    """Decorator to register a primitive class.

    Args:
        cls: Concrete subclass of :class:`Primitive` with a ``name`` attribute.

    Returns:
        The class unchanged (for use as a decorator).

    Raises:
        ValueError: If the class lacks a ``name`` attribute.
    """
    if not cls.name:
        raise ValueError(f"Primitive class {cls.__name__} must have a 'name' attribute")
    _PRIMITIVES[cls.name] = cls
    return cls
