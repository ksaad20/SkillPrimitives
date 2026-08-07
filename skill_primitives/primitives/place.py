"""Place primitive: object is lowered and released."""

from __future__ import annotations

from typing import Any

import numpy as np

from skill_primitives.primitives.base import Primitive


class Place(Primitive):
    """Object is lowered and gripper opens to release.

    Detected from the transition: gripper closed (< 0.5) → open (>= 0.5),
    typically with downward or near-zero z-velocity.
    """

    name = "place"

    def detect(
        self,
        gripper: np.ndarray,
        state: np.ndarray | None = None,
        velocity: np.ndarray | None = None,
    ) -> list[dict[str, Any]]:
        """Detect place segments from gripper opening transitions."""
        segments = []
        if len(gripper) < 2:
            return segments

        vel = velocity if velocity is not None and velocity.size > 0 else self._compute_velocity(state or np.array([]))
        has_velocity = vel.size > 0 and vel.shape[1] >= 3

        for t in range(1, len(gripper)):
            if gripper[t - 1] < 0.5 and gripper[t] >= 0.5:
                # Place release detected
                start = max(0, t - 3)
                end = min(len(gripper), t + 5)

                # Higher confidence if downward or low z-velocity during release
                confidence = 0.88
                if has_velocity and t < len(vel):
                    z_vel = vel[t, 2]
                    if z_vel < -0.001:
                        confidence = 0.95  # Clear downward motion
                    elif abs(z_vel) < 0.005:
                        confidence = 0.92  # Near stationary (gentle place)

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
        return "place the object gently"
