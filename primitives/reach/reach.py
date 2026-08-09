"""Reach primitive — move the end-effector toward a target pose."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class ReachConfig:
    """Configuration for a reach motion."""

    target_position: tuple[float, float, float]
    target_orientation: tuple[float, float, float, float] | None = None
    duration: float = 2.0
    gripper_open: bool = True


class ReachPrimitive:
    """Reach toward a target object or pose.

    Generates a straight-line trajectory in Cartesian space from the
    current end-effector pose to the target pose.
    """

    def __init__(self, config: ReachConfig) -> None:
        self.config = config

    def plan(self, start_pose: dict[str, Any]) -> dict[str, np.ndarray]:
        """Generate a trajectory from *start_pose* to the target.

        Args:
            start_pose: Dict with ``position`` (3,) and ``orientation`` (4,) keys.

        Returns:
            Trajectory dict with ``states`` (N, 7) and ``timestamps`` (N,) arrays.
        """
        start = np.asarray(start_pose["position"], dtype=float)
        target = np.asarray(self.config.target_position, dtype=float)

        num_steps = max(int(self.config.duration * 30), 2)  # 30 Hz
        alphas = np.linspace(0.0, 1.0, num_steps)

        positions = np.outer(1 - alphas, start) + np.outer(alphas, target)

        # Simple linear interpolation for gripper state
        gripper = np.ones(num_steps) * (1.0 if self.config.gripper_open else 0.0)

        states = np.hstack([positions, gripper[:, None]])
        timestamps = np.arange(num_steps) / 30.0

        return {
            "states": states,
            "timestamps": timestamps,
            "primitive_type": "reach",
            "duration": self.config.duration,
        }

    def execute(self, robot_interface: Any) -> None:
        """Execute the planned trajectory on a robot interface.

        This is a stub — replace with your robot-specific control code.
        """
        raise NotImplementedError("ReachPrimitive.execute requires a robot interface.")
