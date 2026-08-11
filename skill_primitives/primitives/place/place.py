"""place.py — Object release primitive at a target location.

Detects place events from demonstration trajectories by identifying
transitions from closed to open gripper states after sustained closed
duration.
"""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np

from skill_primitives.primitives.base import Primitive


class Place(Primitive):
    """Release the grasped object at the target location.

    Detected from the transition: gripper closed (< threshold) → open
    (>= threshold) after sustained closed duration.
    """

    # ── Metadata ───────────────────────────────────────────────────────────
    name: ClassVar[str] = "place"
    version: ClassVar[str] = "0.1.0"
    category: ClassVar[str] = "manipulation"
    description: ClassVar[str] = "Release the grasped object at the target location."
    author: ClassVar[str] = "ksaad20"

    # ── Detection hyperparameters ──────────────────────────────────────────
    OPEN_THRESHOLD: ClassVar[float] = 0.5
    CLOSED_THRESHOLD: ClassVar[float] = 0.5
    PRE_WINDOW: ClassVar[int] = 5
    POST_WINDOW: ClassVar[int] = 3
    MIN_CLOSED_DURATION: ClassVar[int] = 3
    CONFIDENCE_HIGH: ClassVar[float] = 0.92
    CONFIDENCE_LOW: ClassVar[float] = 0.75

    def detect(
        self,
        gripper: np.ndarray,
        state: np.ndarray | None = None,
        velocity: np.ndarray | None = None,
    ) -> list[dict[str, Any]]:
        """Detect place segments from gripper opening transitions.

        Args:
            gripper: 1-D array of normalized gripper openings in [0, 1].
            state: Optional 2-D array of robot states per timestep.
            velocity: Optional 2-D array of velocities per timestep.

        Returns:
            List of segment dicts, each containing ``type``, ``start``,
            ``end``, and ``confidence``.
        """
        segments: list[dict[str, Any]] = []
        n = len(gripper)
        if n < 2:
            return segments

        for t in range(1, n):
            # Transition: closed → open
            if gripper[t - 1] < self.CLOSED_THRESHOLD and gripper[t] >= self.OPEN_THRESHOLD:
                start = max(0, t - self.PRE_WINDOW)
                end = min(n, t + self.POST_WINDOW)

                # Confidence from pre-opening gripper consistency
                pre_start = max(0, t - self.MIN_CLOSED_DURATION)
                pre_closure = gripper[pre_start:t]
                if len(pre_closure) > 0 and np.mean(pre_closure) < self.CLOSED_THRESHOLD:
                    confidence = self.CONFIDENCE_HIGH
                else:
                    confidence = self.CONFIDENCE_LOW

                segments.append(
                    {
                        "type": self.name,
                        "start": int(start),
                        "end": int(end),
                        "confidence": float(confidence),
                    }
                )

        return segments

    def validate(self, segment: dict[str, Any]) -> bool:
        """Check segment quality beyond the default type match.

        Enforces minimum duration and a floor on confidence.
        """
        if not super().validate(segment):
            return False

        duration = segment.get("end", 0) - segment.get("start", 0)
        if duration <= 0:
            return False

        confidence = float(segment.get("confidence", 0.0))
        return confidence >= self.CONFIDENCE_LOW

    def describe(self, segment: dict[str, Any]) -> str:
        """Generate natural-language description with confidence nuance."""
        confidence = float(segment.get("confidence", self.CONFIDENCE_LOW))
        if confidence >= self.CONFIDENCE_HIGH:
            return "place the object carefully"
        return "place the object"
