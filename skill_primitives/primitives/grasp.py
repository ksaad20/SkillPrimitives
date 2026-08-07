"""Grasp primitive: gripper closes to secure an object."""

from __future__ import annotations

from typing import Any

import numpy as np

from skill_primitives.primitives.base import Primitive


class Grasp(Primitive):
    """Gripper closes to secure an object.

    Detected from the transition: gripper open (>= 0.5) → closed (< 0.5).
    The segment spans a short window around the closure point.
    """

    name = "grasp"

    def detect(
        self,
        gripper: np.ndarray,
        state: np.ndarray | None = None,
        velocity: np.ndarray | None = None,
    ) -> list[dict[str, Any]]:
        """Detect grasp segments from gripper closing transitions."""
        segments = []
        if len(gripper) < 2:
            return segments

        for t in range(1, len(gripper)):
            if gripper[t - 1] >= 0.5 and gripper[t] < 0.5:
                # Grasp closure detected
                start = max(0, t - 3)
                end = min(len(gripper), t + 5)

                # Verify: gripper should be mostly closed after transition
                post_closure = gripper[t:min(t + 5, len(gripper))]
                if len(post_closure) > 0 and np.mean(post_closure) < 0.6:
                    confidence = 0.92
                else:
                    confidence = 0.75

                segments.append({
                    "type": self.name,
                    "start": int(start),
                    "end": int(end),
                    "confidence": float(confidence),
                })

        return segments

    def validate(self, segment: dict[str, Any]) -> bool:
        return segment.get("type") == self.name

    def describe(self, segment: dict[str, Any]) -> str:
        return "grasp the object firmly"
