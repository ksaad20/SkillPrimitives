from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np


class Primitive(ABC):
    """Abstract base class for a manipulative skill primitive.

    Subclasses must implement:
    - detect(): Find occurrences in a trajectory
    - validate(): Check a segment is valid

    Subclasses may override:
    - describe(): Generate natural language description
    """

    name: str = ""

    @abstractmethod
    def detect(
        self,
        gripper: np.ndarray,
        state: np.ndarray | None = None,
        velocity: np.ndarray | None = None,
    ) -> list[dict[str, Any]]:
        """Detect occurrences of this primitive in a trajectory.

        Args:
            gripper: Array of shape (T,) with normalized gripper states
                in [0, 1]. Values >= 0.5 indicate open, < 0.5 closed.
            state: Array of shape (T, D) with robot state observations.
                Typically includes end-effector position/orientation.
            velocity: Array of shape (T, 3) with end-effector xyz velocity.
                Pre-computed for efficiency.

        Returns:
            List of segment dicts, each with keys:
            - type: primitive type name
            - start: start frame index (inclusive)
            - end: end frame index (exclusive)
            - confidence: detection confidence in [0.0, 1.0]
        """
        ...

    @abstractmethod
    def validate(self, segment: dict[str, Any]) -> bool:
        """Validate that a detected segment is a valid instance.

        Args:
            segment: Dict with at least type, start, end keys.

        Returns:
            True if the segment is valid for this primitive type.
        """
        ...

    def describe(self, segment: dict[str, Any]) -> str:
        """Generate a natural language description for a segment.

        Override in subclasses for more specific descriptions.

        Args:
            segment: Detected segment dict.

        Returns:
            Natural language command string.
        """
        return f"perform {self.name}"

    def _compute_velocity(self, state: np.ndarray) -> np.ndarray:
        """Compute end-effector velocity from state.

        Convenience method for subclasses that need velocity
        but receive only state.

        Args:
            state: Array of shape (T, D) with state observations.

        Returns:
            Array of shape (T, 3) with xyz velocity.
        """
        if state.size == 0 or state.shape[1] < 3:
            return np.array([])
        pos = state[:, :3].astype(float)
        vel = np.zeros_like(pos)
        vel[1:] = pos[1:] - pos[:-1]
        return vel

    def _gripper_is_open(self, gripper: np.ndarray, start: int, end: int) -> bool:
        """Check if gripper is predominantly open in a frame range.

        Args:
            gripper: Array of shape (T,) with gripper states.
            start: Start frame.
            end: End frame.

        Returns:
            True if mean gripper state >= 0.4 (mostly open).
        """
        if start >= end or start >= len(gripper):
            return False
        return float(np.mean(gripper[start:end])) >= 0.4

    def _gripper_is_closed(self, gripper: np.ndarray, start: int, end: int) -> bool:
        """Check if gripper is predominantly closed in a frame range.

        Args:
            gripper: Array of shape (T,) with gripper states.
            start: Start frame.
            end: End frame.

        Returns:
            True if mean gripper state < 0.6 (mostly closed).
        """
        if start >= end or start >= len(gripper):
            return False
        return float(np.mean(gripper[start:end])) < 0.6
