"""Reach primitive: gripper open, approaching target object."""

from __future__ import annotations

from typing import Any

import numpy as np

from skill_primitives.primitives.base import Primitive


class Reach(Primitive):
    """Arm moves toward target object with gripper open.

    Detected as motion toward the target (decreasing distance)
    while the gripper remains open, occurring before a grasp.
    """

    name = "reach"

    def detect(
        self,
        gripper: np.ndarray,
        state: np.ndarray | None = None,
        velocity: np.ndarray | None = None,
    ) -> list[dict[str, Any]]:
        """Detect reach segments.

        Strategy: Look for periods of motion with gripper open
        that precede grasping. We approximate by finding motion
        peaks before gripper closure transitions.
        """
        segments: list[dict[str, Any]] = []
        if len(gripper) < 5:
            return segments

        # Compute velocity if not provided
        vel = (
            velocity
            if velocity is not None and velocity.size > 0
            else self._compute_velocity(state or np.array([]))
        )
        if vel.size == 0:
            return segments

        vel_mag = np.linalg.norm(vel, axis=1)

        # Find all grasp transitions to anchor reach detection
        grasp_starts = []
        for t in range(1, len(gripper)):
            if gripper[t - 1] >= 0.5 and gripper[t] < 0.5:
                grasp_starts.append(t)

        # If no grasps found, look for any open-gripper motion
        if not grasp_starts:
            # Find sustained motion with open gripper
            for t in range(len(gripper) - 5):
                if self._gripper_is_open(gripper, t, t + 5) and np.mean(vel_mag[t : t + 5]) > 0.01:
                    segments.append(
                        {
                            "type": self.name,
                            "start": int(t),
                            "end": int(t + 5),
                            "confidence": 0.75,
                        }
                    )
            return segments

        # Detect reach before each grasp
        for grasp_t in grasp_starts:
            search_start = max(0, grasp_t - 20)
            search_end = grasp_t

            if search_end <= search_start:
                continue

            # Find peak velocity in the window before grasp
            window_vel = vel_mag[search_start:search_end]
            if len(window_vel) == 0 or np.max(window_vel) < 0.005:
                continue

            peak_idx = search_start + int(np.argmax(window_vel))

            # Expand window around peak while gripper is open
            reach_start = peak_idx
            while reach_start > search_start and gripper[reach_start] >= 0.4:
                reach_start -= 1
            reach_start = max(0, reach_start)

            reach_end = min(grasp_t + 2, len(gripper))

            # Verify gripper is open during reach
            if not self._gripper_is_open(gripper, reach_start, min(reach_end, len(gripper))):
                continue

            segments.append(
                {
                    "type": self.name,
                    "start": int(reach_start),
                    "end": int(reach_end),
                    "confidence": 0.88,
                }
            )

        return segments

    def validate(self, segment: dict[str, Any]) -> bool:
        return segment.get("type") == self.name

    def describe(self, segment: dict[str, Any]) -> str:
        return "reach toward the target object"
