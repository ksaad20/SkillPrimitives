"""reach.py — Pre-grasp approach primitive toward a target object.

Detects reach events from demonstration trajectories by identifying
sustained end-effector motion while the gripper remains open.
"""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np

from skill_primitives.primitives.base import Primitive


class Reach(Primitive):
    """Move the open gripper toward the target object.

    Detected from sustained end-effector motion while the gripper
    remains open.
    """

    # ── Metadata ───────────────────────────────────────────────────────────
    name: ClassVar[str] = "reach"
    version: ClassVar[str] = "0.1.0"
    category: ClassVar[str] = "manipulation"
    description: ClassVar[str] = "Move the open gripper toward the target object."
    author: ClassVar[str] = "ksaad20"

    # ── Detection hyperparameters ──────────────────────────────────────────
    OPEN_THRESHOLD: ClassVar[float] = 0.5
    MIN_SPEED_THRESHOLD: ClassVar[float] = 0.01
    MIN_DURATION: ClassVar[int] = 3
    PRE_WINDOW: ClassVar[int] = 3
    POST_WINDOW: ClassVar[int] = 2

    def detect(
        self,
        gripper: np.ndarray,
        state: np.ndarray | None = None,
        velocity: np.ndarray | None = None,
    ) -> list[dict[str, Any]]:
        """Detect reach segments from open-gripper motion.

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

        speed = self._compute_speed(state, velocity, n)
        if speed is None:
            return segments

        open_mask = gripper >= self.OPEN_THRESHOLD

        i = 0
        while i < n:
            if not open_mask[i]:
                i += 1
                continue

            start = i
            while i < n and open_mask[i]:
                i += 1
            end = i

            if end - start < self.MIN_DURATION:
                continue

            mean_speed = float(np.mean(speed[start:end]))
            if mean_speed >= self.MIN_SPEED_THRESHOLD:
                confidence = self._compute_confidence(mean_speed)
                seg_start = max(0, start - self.PRE_WINDOW)
                seg_end = min(n, end + self.POST_WINDOW)
                segments.append(
                    {
                        "type": self.name,
                        "start": int(seg_start),
                        "end": int(seg_end),
                        "confidence": float(confidence),
                    }
                )

        return segments

    def _compute_speed(
        self,
        state: np.ndarray | None,
        velocity: np.ndarray | None,
        n: int,
    ) -> np.ndarray | None:
        """Return per-timestep speed, preferring velocity norm over state deltas."""
        if velocity is not None and velocity.ndim == 2 and velocity.shape[0] == n:
            speed: np.ndarray = np.linalg.norm(velocity, axis=1)
            return speed
        if state is not None and state.ndim == 2 and state.shape[0] == n:
            deltas = np.diff(state, axis=0, prepend=state[:1])
            speed = np.linalg.norm(deltas, axis=1)
            return speed
        return None

    def _compute_confidence(self, mean_speed: float) -> float:
        """Higher confidence for faster, clearer approach motion."""
        if mean_speed > 0.05:
            return 0.93
        if mean_speed > 0.02:
            return 0.85
        return 0.78

    def validate(self, segment: dict[str, Any]) -> bool:
        """Check segment quality beyond the default type match."""
        if not super().validate(segment):
            return False

        duration = segment.get("end", 0) - segment.get("start", 0)
        if duration <= 0:
            return False

        confidence = float(segment.get("confidence", 0.0))
        return confidence >= 0.75

    def describe(self, segment: dict[str, Any]) -> str:
        """Generate natural-language description with confidence nuance."""
        confidence = float(segment.get("confidence", 0.0))
        if confidence >= 0.9:
            return "reach toward the object quickly"
        return "reach toward the object"
