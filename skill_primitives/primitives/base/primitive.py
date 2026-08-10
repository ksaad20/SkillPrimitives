"""Base class for skill primitives.

All concrete primitives (reach, grasp, lift, transport, place) inherit from
:class:`Primitive` and implement the :meth:`detect`, :meth:`validate`, and
:meth:`describe` methods.
"""

from __future__ import annotations

from typing import Any

import numpy as np


class Primitive:
    """Abstract base class for a manipulation primitive.

    Subclasses must set the ``name`` class attribute and override
    :meth:`detect`, :meth:`validate`, and :meth:`describe`.
    """

    name: str = ""

    def detect(
        self,
        gripper: np.ndarray,
        state: np.ndarray | None = None,
        velocity: np.ndarray | None = None,
    ) -> list[dict[str, Any]]:
        """Detect segments of this primitive in a trajectory.

        Args:
            gripper: 1-D array of gripper open/close values. Values >= 0.5
                are considered open; < 0.5 are closed.
            state: Optional array of shape ``(T, D)`` with Cartesian state
                (e.g. end-effector position).
            velocity: Optional array of shape ``(T, D)`` with Cartesian
                velocity. If ``None``, it is computed from *state*.

        Returns:
            List of segment dictionaries, each containing at least
            ``type``, ``start``, ``end``, and ``confidence``.
        """
        raise NotImplementedError

    def validate(self, segment: dict[str, Any]) -> bool:
        """Return whether *segment* is a valid instance of this primitive."""
        raise NotImplementedError

    def describe(self, segment: dict[str, Any]) -> str:
        """Return a natural-language description of *segment*."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Shared helpers used by concrete primitives
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_velocity(state: np.ndarray) -> np.ndarray:
        """Compute finite-difference velocity from *state*.

        Args:
            state: Array of shape ``(T, D)``.

        Returns:
            Array of shape ``(T, D)`` where the first row is zeros.
        """
        if state.size == 0 or state.ndim < 2:
            return np.array([])
        vel = np.zeros_like(state)
        vel[1:] = np.diff(state, axis=0)
        return vel

    @staticmethod
    def _gripper_is_open(
        gripper: np.ndarray, start: int, end: int, threshold: float = 0.4
    ) -> bool:
        """Return ``True`` if gripper is open across ``[start, end)``.

        Args:
            gripper: 1-D gripper signal.
            start: Inclusive start index.
            end: Exclusive end index.
            threshold: Values >= *threshold* count as open.
        """
        if start >= len(gripper) or end > len(gripper):
            return False
        return bool(np.all(gripper[start:end] >= threshold))
