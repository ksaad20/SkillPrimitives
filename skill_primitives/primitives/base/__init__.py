"""base — Abstract foundation for all robotics annotation primitives.

This module defines the core :class:`Primitive` abstraction that every
concrete primitive (grasp, reach, retract, etc.) must subclass.
"""

from __future__ import annotations

from base.base import Primitive

__all__ = [
    "Primitive",
]
