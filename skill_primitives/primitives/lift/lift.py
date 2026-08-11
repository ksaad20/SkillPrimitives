"""lift.py — Vertical lift primitive after object acquisition.

Detects lift events from demonstration trajectories by identifying
sustained upward end-effector displacement while the gripper remains
closed.
"""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np

from skill_primitives.primitives.base import Primitive


class Lift(Primitive):
    """Lift the grasped object vertically.

    Detected from sustained upward Z displacement while the gripper
    remains closed.
    """

    # ── Metadata ───────────────────────────────────────────────────────────
    name: ClassVar[str] = "lift"
    version: ClassVar[str] = "0.1.0"
    category: ClassVar[str] = "manipulation"
    description: ClassVar[str] = "Lift the grasped object vertically."
    author: ClassVar[str] = "ksaad20"

    # ── Detection hyperparameters ──────────────────────────────────────────
    CLOSED_THRESHOLD: ClassVar[float] = 0.5
    Z_RISE_THRESHOLD: ClassVar[float] = 0.02
    MIN_DURATION: ClassVar[int] = 5
    Z_INDEX: ClassVar[int] = 2

    def detect(
        self,
        gripper: np.ndarray,
        state: np.ndarray | None = None,
        velocity: np.ndarray | None = None,
    ) -> list[dict[str, Any]]:
        """Detect lift segments from upward Z motion with closed gripper.

        Args:
            gripper: 1-D array of normalized gripper openings in [0, 1].
            state: 2-D array of robot states per timestep. The Z position
                is expected at column :attr:`Z_INDEX`.
            velocity: Optional 2-D array of velocities per timestep.

        Returns:
            List of segment dicts, each containing ``type``, ``start``,
            ``end``, and ``confidence``.
        """
        segments: list[dict[str, Any]] = []
        if state is None or len(gripper) < 2:
            return segments

        n = len(gripper)
        if state.ndim != 2 or state.shape[0] != n:
            return segments

        z = state[:, self.Z_INDEX]
        closed = gripper < self.CLOSED_THRESHOLD

        i = 0
        while i < n:
            if not closed[i]:
                i += 1
                continue

            start = i
            while i < n and closed[i]:
                i += 1
            end = i

            if end - start < self.MIN_DURATION:
                continue

            z_rise = float(z[end - 1] - z[start])
            if z_rise >= self.Z_RISE_THRESHOLD:
                confidence = self._compute_confidence(z_rise)
                segments.append(
                    {
                        "type": self.name,
                        "start": int(start),
                        "end": int(end),
                        "confidence": float(confidence),
                    }
                )

        return segments

    def _compute_confidence(self, z_rise: float) -> float:
        """Higher confidence for larger, clearer Z displacement."""
        if z_rise > 0.1:
            return 0.95
        if z_rise > 0.05:
            return 0.88
        return 0.80

    def validate(self, segment: dict[str, Any]) -> bool:
        """Check segment quality beyond the default type match."""
        if not super().validate(segment):
            return False

        duration = segment.get("end", 0) - segment.get("start", 0)
        if duration < self.MIN_DURATION:
            return False

        confidence = float(segment.get("confidence", 0.0))
        return confidence >= 0.75

    def describe(self, segment: dict[str, Any]) -> str:
        """Generate natural-language description with confidence nuance."""
        confidence = float(segment.get("confidence", 0.0))
        if confidence >= 0.9:
            return "lift the object steadily"
        return "lift the object"
