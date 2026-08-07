"""Transport primitive: object moves horizontally with gripper closed."""

from __future__ import annotations

from typing import Any

import numpy as np

from skill_primitives.primitives.base import Primitive


class Transport(Primitive):
    """Object is moved horizontally to a new location.

    Detected as sustained horizontal motion (xy plane) with
    gripper closed, between a lift and a place.
    """

    name = "transport"

    def detect(
        self,
        gripper: np.ndarray,
        state: np.ndarray | None = None,
        velocity: np.ndarray | None = None,
    ) -> list[dict[str, Any]]:
        """Detect transport segments: horizontal motion with closed gripper."""
        segments = []
        if len(gripper) < 3:
            return segments

        vel = (
            velocity
            if velocity is not None and velocity.size > 0
            else self._compute_velocity(state or np.array([]))
        )
        if vel.size == 0 or vel.shape[1] < 2:
            return segments

        xy_vel = vel[:, :2]
        xy_mag = np.linalg.norm(xy_vel, axis=1)
        min_transport_frames = 3
        xy_threshold = 0.005

        t = 0
        while t < len(xy_mag):
            # Look for horizontal motion with closed gripper
            if xy_mag[t] > xy_threshold and gripper[t] < 0.5:
                start = t
                while t < len(xy_mag) and xy_mag[t] > xy_threshold and gripper[t] < 0.5:
                    t += 1
                end = t

                if end - start >= min_transport_frames:
                    segments.append(
                        {
                            "type": self.name,
                            "start": int(start),
                            "end": int(end),
                            "confidence": 0.85,
                        }
                    )
            else:
                t += 1

        return segments

    def validate(self, segment: dict[str, Any]) -> bool:
        return segment.get("type") == self.name

    def describe(self, segment: dict[str, Any]) -> str:
        return "transport the object to the destination"
