"""Lift primitive: object moves upward with gripper closed."""

from __future__ import annotations

from typing import Any

import numpy as np

from skill_primitives.primitives.base import Primitive


class Lift(Primitive):
    """Object is lifted vertically while secured by gripper.

    Detected as sustained positive z-velocity with gripper closed,
    occurring after a grasp.
    """

    name = "lift"

    def detect(
        self,
        gripper: np.ndarray,
        state: np.ndarray | None = None,
        velocity: np.ndarray | None = None,
    ) -> list[dict[str, Any]]:
        """Detect lift segments: positive z-velocity with closed gripper."""
        segments = []
        if len(gripper) < 3:
            return segments

        vel = (
            velocity
            if velocity is not None and velocity.size > 0
            else self._compute_velocity(state or np.array([]))
        )
        if vel.size == 0 or vel.shape[1] < 3:
            return segments

        z_vel = vel[:, 2]
        min_lift_frames = 3
        z_threshold = 0.005

        t = 0
        while t < len(z_vel):
            # Look for start of upward motion
            if z_vel[t] > z_threshold and gripper[t] < 0.5:
                start = t
                # Extend while z-velocity stays positive and gripper closed
                while t < len(z_vel) and z_vel[t] > z_threshold and gripper[t] < 0.5:
                    t += 1
                end = t

                if end - start >= min_lift_frames:
                    segments.append(
                        {
                            "type": self.name,
                            "start": int(start),
                            "end": int(end),
                            "confidence": 0.90,
                        }
                    )
            else:
                t += 1

        return segments

    def validate(self, segment: dict[str, Any]) -> bool:
        return segment.get("type") == self.name

    def describe(self, segment: dict[str, Any]) -> str:
        return "lift the object vertically"
