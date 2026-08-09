"""Heuristic trajectory segmentation for LeRobot datasets.

Segments robot manipulation episodes into discrete primitives
(reach, grasp, lift, transport, place) using gripper state transitions
and end-effector motion heuristics.
"""

from __future__ import annotations

from typing import Any

import numpy as np


class Segmenter:
    """Segment a robot manipulation episode into discrete skill primitives."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def segment(self, episode: dict[str, Any]) -> list[dict[str, Any]]:
        """Segment an already-loaded episode into discrete primitives.

        Args:
            episode: Dict with at least ``actions`` (T, action_dim) and
                ``observations`` or ``state`` (T, state_dim).

        Returns:
            List of primitive dicts sorted by start frame, each with keys:
            type, start, end, confidence.
        """
        actions = episode.get("actions", np.array([]))
        state = episode.get("state", episode.get("observations", np.array([])))

        if actions.size == 0:
            return []

        gripper = self._extract_gripper_state(actions)
        velocity = self._extract_end_effector_velocity(state)

        grasp_segments = self._detect_grasp_segments(gripper)
        place_segments = self._detect_place_segments(gripper)
        reach_segments = self._detect_reach_segments(gripper, velocity, grasp_segments)
        lift_segments = self._detect_lift_segments(gripper, velocity, grasp_segments)
        transport_segments = self._detect_transport_segments(
            gripper, velocity, lift_segments, place_segments
        )

        all_segments = (
            grasp_segments + place_segments + reach_segments + lift_segments + transport_segments
        )
        all_segments.sort(key=lambda s: s["start"])
        return self._merge_overlapping_segments(all_segments)

    @staticmethod
    def load_lerobot_episode(
        dataset_name: str, episode: int = 0, *, revision: str
    ) -> dict[str, Any]:
        """Load a single episode from a LeRobot dataset on HuggingFace.

        Args:
            dataset_name: HuggingFace dataset ID (e.g., "lerobot/pusht").
            episode: Episode index to load.
            revision: Specific git revision (commit hash or tag) to pin
                the dataset version. Required for reproducibility.

        Returns:
            Dict with keys: observations, actions, timestamps, episode_index.
        """
        try:
            from datasets import load_dataset
        except ImportError as err:
            raise ImportError(
                "The 'datasets' library is required to load LeRobot datasets. "
                "Install it with: pip install datasets"
            ) from err

        ds = load_dataset(dataset_name, split="train", streaming=False, revision=revision)

        if "episode_index" in ds.column_names:
            episode_data = ds.filter(lambda x: x["episode_index"] == episode)
        else:
            episode_data = ds

        result: dict[str, Any] = {
            "episode_index": episode,
            "dataset_name": dataset_name,
            "num_frames": len(episode_data),
        }

        if "action" in episode_data.column_names:
            result["actions"] = np.array(episode_data["action"])
        else:
            result["actions"] = np.array([])

        if "observation.state" in episode_data.column_names:
            result["state"] = np.array(episode_data["observation.state"])
        elif "state" in episode_data.column_names:
            result["state"] = np.array(episode_data["state"])
        else:
            result["state"] = np.array([])

        if "timestamp" in episode_data.column_names:
            result["timestamps"] = np.array(episode_data["timestamp"])
        else:
            result["timestamps"] = np.arange(len(episode_data))

        if "frame_index" in episode_data.column_names:
            result["frame_indices"] = np.array(episode_data["frame_index"])
        else:
            result["frame_indices"] = np.arange(len(episode_data))

        return result

    # ------------------------------------------------------------------
    # Feature extraction
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_gripper_state(actions: np.ndarray) -> np.ndarray:
        """Extract gripper open/closed state from action array."""
        if actions.size == 0:
            return np.array([])

        gripper = actions[:, -1].astype(float)
        g_min, g_max = gripper.min(), gripper.max()
        if g_max > g_min:
            gripper = (gripper - g_min) / (g_max - g_min)
        return gripper

    @staticmethod
    def _extract_end_effector_velocity(state: np.ndarray) -> np.ndarray:
        """Compute end-effector velocity from state (first 3 dims = xyz)."""
        if state.size == 0 or state.shape[1] < 3:
            return np.array([])

        pos = state[:, :3].astype(float)
        vel = np.zeros_like(pos)
        vel[1:] = pos[1:] - pos[:-1]
        return vel

    # ------------------------------------------------------------------
    # Primitive detectors
    # ------------------------------------------------------------------
    @staticmethod
    def _detect_grasp_segments(gripper: np.ndarray) -> list[dict[str, Any]]:
        """Detect grasp primitives from gripper closing transitions."""
        segments: list[dict[str, Any]] = []
        if len(gripper) < 2:
            return segments

        for t in range(1, len(gripper)):
            if gripper[t - 1] >= 0.5 and gripper[t] < 0.5:
                start = max(0, t - 3)
                end = min(len(gripper), t + 5)
                segments.append(
                    {
                        "type": "grasp",
                        "start": int(start),
                        "end": int(end),
                        "confidence": 0.92,
                    }
                )
        return segments

    @staticmethod
    def _detect_place_segments(gripper: np.ndarray) -> list[dict[str, Any]]:
        """Detect place primitives from gripper opening transitions."""
        segments: list[dict[str, Any]] = []
        if len(gripper) < 2:
            return segments

        for t in range(1, len(gripper)):
            if gripper[t - 1] < 0.5 and gripper[t] >= 0.5:
                start = max(0, t - 3)
                end = min(len(gripper), t + 5)
                segments.append(
                    {
                        "type": "place",
                        "start": int(start),
                        "end": int(end),
                        "confidence": 0.90,
                    }
                )
        return segments

    def _detect_reach_segments(
        self,
        gripper: np.ndarray,
        velocity: np.ndarray,
        grasp_segments: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Detect reach primitives: approaching motion before a grasp."""
        segments: list[dict[str, Any]] = []
        if len(gripper) == 0 or len(velocity) == 0:
            return segments

        for grasp in grasp_segments:
            search_start = max(0, grasp["start"] - 15)
            search_end = grasp["start"]

            if search_end <= search_start:
                continue

            vel_mag = np.linalg.norm(velocity[search_start:search_end], axis=1)
            if len(vel_mag) == 0:
                continue

            peak_idx = search_start + int(np.argmax(vel_mag))
            reach_start = max(0, peak_idx - 5)
            reach_end = min(len(gripper), grasp["start"] + 2)

            if np.mean(gripper[reach_start:reach_end]) >= 0.4:
                segments.append(
                    {
                        "type": "reach",
                        "start": int(reach_start),
                        "end": int(reach_end),
                        "confidence": 0.88,
                    }
                )
        return segments

    def _detect_lift_segments(
        self,
        gripper: np.ndarray,
        velocity: np.ndarray,
        grasp_segments: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Detect lift primitives: vertical motion after grasp."""
        segments: list[dict[str, Any]] = []
        if len(gripper) == 0 or len(velocity) == 0:
            return segments

        for grasp in grasp_segments:
            search_start = grasp["end"]
            search_end = min(len(gripper), grasp["end"] + 15)

            if search_end <= search_start:
                continue

            z_vel = velocity[search_start:search_end, 2]
            if len(z_vel) == 0:
                continue

            positive_z = z_vel > 0.01
            if not np.any(positive_z):
                continue

            lift_start = search_start + int(np.argmax(positive_z))
            negative_after = np.where(z_vel[int(np.argmax(positive_z)) :] <= 0.01)[0]
            lift_end = (
                 lift_start + int(negative_after[0]) if len(negative_after) > 0 
else search_end
             )

            if np.mean(gripper[lift_start:lift_end]) < 0.6:
                segments.append(
                    {
                        "type": "lift",
                        "start": int(lift_start),
                        "end": int(lift_end),
                        "confidence": 0.85,
                    }
                )
        return segments

    def _detect_transport_segments(
        self,
        gripper: np.ndarray,
        velocity: np.ndarray,
        lift_segments: list[dict[str, Any]],
        place_segments: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Detect transport primitives: horizontal motion between lift and place."""
        segments: list[dict[str, Any]] = []
        if len(gripper) == 0 or len(velocity) == 0:
            return segments

        for lift in lift_segments:
            next_place = None
            for place in place_segments:
                if place["start"] > lift["end"]:
                    next_place = place
                    break

            if next_place is None:
                continue

            search_start = lift["end"]
            search_end = next_place["start"]

            if search_end <= search_start:
                continue

            xy_vel = velocity[search_start:search_end, :2]
            xy_mag = np.linalg.norm(xy_vel, axis=1)

            if len(xy_mag) == 0 or np.max(xy_mag) < 0.01:
                continue

            motion_start = search_start + int(np.argmax(xy_mag > 0.01))
            motion_end = search_end

            if np.mean(gripper[motion_start:motion_end]) < 0.6:
                segments.append(
                    {
                        "type": "transport",
                        "start": int(motion_start),
                        "end": int(motion_end),
                        "confidence": 0.82,
                    }
                )
        return segments

    @staticmethod
    def _merge_overlapping_segments(
        segments: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Merge overlapping or adjacent segments of the same type."""
        if not segments:
            return []

        merged = [segments[0].copy()]
        for seg in segments[1:]:
            last = merged[-1]
            if seg["type"] == last["type"] and seg["start"] <= last["end"]:
                last["end"] = max(last["end"], seg["end"])
                last["confidence"] = max(last["confidence"], seg["confidence"])
            else:
                merged.append(seg.copy())
        return merged
