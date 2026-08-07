"""Skill primitive detectors and registry.

Provides concrete implementations of manipulation primitives
(reach, grasp, lift, transport, place) and a central registry
for discovery and instantiation.
"""

from skill_primitives.primitives.base import Primitive
from skill_primitives.primitives.reach import Reach
from skill_primitives.primitives.grasp import Grasp
from skill_primitives.primitives.lift import Lift
from skill_primitives.primitives.transport import Transport
from skill_primitives.primitives.place import Place
from skill_primitives.primitives.registry import (
    get_primitive,
    list_primitives,
    get_all_primitives,
    register_primitive,
    create_detector,
    detect_all,
)

__all__ = [
    "Primitive",
    "Reach",
    "Grasp",
    "Lift",
    "Transport",
    "Place",
    "get_primitive",
    "list_primitives",
    "get_all_primitives",
    "register_primitive",
    "create_detector",
    "detect_all",
]
