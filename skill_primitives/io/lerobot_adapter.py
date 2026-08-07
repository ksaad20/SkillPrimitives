"""Adapter for LeRobot datasets on HuggingFace.

Loads episodes from LeRobot-format datasets and standardizes
them for the Skill Primitives pipeline.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from skill_primitives.io.base import BaseAdapter


class LeRobotAdapter(BaseAdapter):
    """Load episodes from HuggingFace LeRobot datasets.

    LeRobot datasets use the `datasets` library format with columns:
    - observation.state or state: robot joint/EE states
    - action: action commands (last dim is typically gripper)
    - episode_index: which episode each frame belongs to
    - frame_index: frame number within episode
    - timestamp: time in seconds
    - observation.image (optional): camera images
    """

    def load_episode(self, dataset_path: str, episode_index: int = 0) -> dict[str, Any]:
        """Load a single episode from a LeRobot dataset.

        Args:
            dataset_path: HuggingFace dataset ID (e.g., "lerobot/pusht").
            episode_index: Episode index to load.

        Returns:
            Standardized episode dict.
        """
        try:
            from datasets import load_dataset
        except ImportError:
            raise ImportError(
                "The 'datasets' library is required. " "Install with: pip install datasets"
            )

        ds = load_dataset(
    dataset_path, split="train", streaming=False, revision="main"
)  # nosec B615 - intentionally tracking main branch for latest data

        # Filter to specific episode
        if "episode_index" in ds.column_names:
            episode_data = ds.filter(lambda x: x["episode_index"] == episode_index)
        else:
            # Single episode dataset or no episode index
            episode_data = ds

        num_frames = len(episode_data)
        if num_frames == 0:
            raise ValueError(f"Episode {episode_index} not found in {dataset_path}")

        result: dict[str, Any] = {
            "dataset_path": dataset_path,
            "episode_index": episode_index,
            "num_frames": num_frames,
        }

        # Extract actions (shape: T x action_dim, last dim is gripper)
        if "action" in episode_data.column_names:
            actions = np.array(episode_data["action"])
            result["actions"] = actions
            result["action_dim"] = actions.shape[1] if actions.ndim > 1 else 1
        else:
            result["actions"] = np.array([])
            result["action_dim"] = 0

        # Extract state/observations
        state_key = None
        for key in ["observation.state", "state", "observation"]:
            if key in episode_data.column_names:
                state_key = key
                break

        if state_key:
            states = np.array(episode_data[state_key])
            result["states"] = states
            result["state_dim"] = states.shape[1] if states.ndim > 1 else 1
        else:
            result["states"] = np.array([])
            result["state_dim"] = 0

        # Extract timestamps
        if "timestamp" in episode_data.column_names:
            result["timestamps"] = np.array(episode_data["timestamp"])
        else:
            result["timestamps"] = np.arange(num_frames) * 0.05  # 20Hz default

        # Extract frame indices
        if "frame_index" in episode_data.column_names:
            result["frame_indices"] = np.array(episode_data["frame_index"])
        else:
            result["frame_indices"] = np.arange(num_frames)

        # Extract gripper states from last action dimension
        if "actions" in result and result["actions"].size > 0:
            actions = result["actions"]
            if actions.ndim > 1 and actions.shape[1] > 0:
                gripper = actions[:, -1].astype(float)
                g_min, g_max = gripper.min(), gripper.max()
                if g_max > g_min:
                    gripper = (gripper - g_min) / (g_max - g_min)
                result["gripper_states"] = gripper
            else:
                result["gripper_states"] = np.ones(num_frames)
        else:
            result["gripper_states"] = np.ones(num_frames)

        # Extract images if available
        for img_key in ["observation.image", "image"]:
            if img_key in episode_data.column_names:
                result["images"] = list(episode_data[img_key])
                break

        # Episode metadata
        result["metadata"] = {
            "dataset": dataset_path,
            "episode": episode_index,
            "num_frames": num_frames,
            "fps": 20.0,
        }

        return result

    def list_episodes(self, dataset_path: str) -> list[int]:
        """List available episode indices in a LeRobot dataset.

        Args:
            dataset_path: HuggingFace dataset ID.

        Returns:
            List of episode index integers.
        """
        try:
            from datasets import load_dataset
        except ImportError:
            raise ImportError(
                "The 'datasets' library is required. " "Install with: pip install datasets"
            )

        ds = load_dataset(
    dataset_path, split="train", streaming=False, revision="main"
)  # nosec B615 - intentionally tracking main branch for latest data

        if "episode_index" in ds.column_names:
            episodes = sorted(set(ds["episode_index"]))
            return [int(e) for e in episodes]
        else:
            # Single episode
            return [0]
