"""grasp.py — Gripper closure primitive for object acquisition.

Detects grasp events from demonstration trajectories by identifying
transitions from open to closed gripper states. Emits segments with
confidence scores derived from post-closure gripper consistency.
"""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np

from skill_primitives.primitives.base import Primitive


class Grasp(Primitive):
    """Gripper closes to secure an object.

    Detected from the transition: gripper open (>= threshold) → closed
    (< threshold). The segment spans a short temporal window around the
    closure point.
    """

    # ── Metadata ───────────────────────────────────────────────────────────
    name: ClassVar[str] = "grasp"
    version: ClassVar[str] = "0.1.0"
    category: ClassVar[str] = "grasp"
    description: ClassVar[str] = "Gripper closes to secure an object."
    author: ClassVar[str] = "ksaad20"

    # ── Detection hyperparameters ──────────────────────────────────────────
    OPEN_THRESHOLD: ClassVar[float] = 0.5
    CLOSED_THRESHOLD: ClassVar[float] = 0.5
    PRE_WINDOW: ClassVar[int] = 3
    POST_WINDOW: ClassVar[int] = 5
    CONFIDENCE_HIGH: ClassVar[float] = 0.92
    CONFIDENCE_LOW: ClassVar[float] = 0.75
    POST_MEAN_THRESHOLD: ClassVar[float] = 0.6

    def detect(
        self,
        gripper: np.ndarray,
        state: np.ndarray | None = None,
        velocity: np.ndarray | None = None,
    ) -> list[dict[str, Any]]:
        """Detect grasp segments from gripper closing transitions.

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
            # Transition: open → closed
            if gripper[t - 1] >= self.OPEN_THRESHOLD and gripper[t] < self.CLOSED_THRESHOLD:
                start = max(0, t - self.PRE_WINDOW)
                end = min(n, t + self.POST_WINDOW)

                # Confidence from post-closure consistency
                post_end = min(t + self.POST_WINDOW, n)
                post_closure = gripper[t:post_end]
                if len(post_closure) > 0 and np.mean(post_closure) < self.POST_MEAN_THRESHOLD:
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
            return "grasp the object firmly"
        return "grasp the object"
