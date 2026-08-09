from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def import_data(path: str, **kwargs: Any) -> dict[str, Any]:
    """Import a trajectory from a CSV file.

    Expected columns (case-insensitive):
    - time or timestamp: time in seconds
    - joint_0, joint_1, ... or state_0, state_1, ...: state observations
    - action_0, action_1, ...: action commands
    - gripper: gripper state (0=closed, 1=open or normalized)

    Args:
        path: Path to CSV file.
        **kwargs: Additional arguments passed to pandas.read_csv.

    Returns:
        Standardized episode dict.
    """
    df = pd.read_csv(path, **kwargs)

    # Normalize column names to lowercase
    df.columns = [c.lower().strip() for c in df.columns]

    result: dict[str, Any] = {
        "source_path": path,
        "num_frames": len(df),
    }

    # Extract timestamps
    for key in ("time", "timestamp", "t"):
        if key in df.columns:
            result["timestamps"] = df[key].values
            break
    else:
        result["timestamps"] = np.arange(len(df)) * 0.05

    # Extract state (joint or state columns)
    state_cols = [c for c in df.columns if c.startswith(("joint_", "state_", "q_"))]
    if state_cols:
        result["states"] = df[state_cols].values
        result["state_dim"] = len(state_cols)
    else:
        # Try to infer state from remaining numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        exclude = ("time", "timestamp", "t", "gripper")
        state_cols = [c for c in numeric_cols if c not in exclude]
        if state_cols:
            result["states"] = df[state_cols].values
            result["state_dim"] = len(state_cols)
        else:
            result["states"] = np.array([])
            result["state_dim"] = 0

    # Extract actions
    action_cols = [c for c in df.columns if c.startswith(("action_", "a_", "cmd_"))]
    if action_cols:
        result["actions"] = df[action_cols].values
        result["action_dim"] = len(action_cols)
    else:
        result["actions"] = np.array([])
        result["action_dim"] = 0

    # Extract gripper state
    if "gripper" in df.columns:
        gripper = df["gripper"].values.astype(float)
        g_min, g_max = gripper.min(), gripper.max()
        if g_max > g_min:
            gripper = (gripper - g_min) / (g_max - g_min)
        result["gripper_states"] = gripper
    elif result["actions"].size > 0 and result["actions"].ndim > 1:
        # Infer from last action dimension
        gripper = result["actions"][:, -1].astype(float)
        g_min, g_max = gripper.min(), gripper.max()
        if g_max > g_min:
            gripper = (gripper - g_min) / (g_max - g_min)
        result["gripper_states"] = gripper
    else:
        result["gripper_states"] = np.ones(len(df))

    result["metadata"] = {
        "source": "csv",
        "path": path,
        "num_frames": len(df),
        "columns": list(df.columns),
    }

    return result


def import_hdf5(path: str, dataset_key: str = "trajectory") -> dict[str, Any]:
    """Import a trajectory from an HDF5 file.

    Args:
        path: Path to HDF5 file.
        dataset_key: Key for the trajectory dataset within the file.

    Returns:
        Standardized episode dict.
    """
    try:
        import h5py
    except ImportError as err:
        raise ImportError(
            "h5py is required for HDF5 import. Install with: pip install h5py"
        ) from err

    with h5py.File(path, "r") as f:
        if dataset_key not in f:
            available = list(f.keys())
            raise KeyError(
                f"Dataset '{dataset_key}' not found in {path}. " f"Available keys: {available}"
            )

        data = f[dataset_key]

        result: dict[str, Any] = {
            "source_path": path,
            "num_frames": data.shape[0] if hasattr(data, "shape") else 0,
        }

        # Try to extract common datasets
        if "actions" in f:
            result["actions"] = np.array(f["actions"])
        if "states" in f or "observations" in f:
            key = "states" if "states" in f else "observations"
            result["states"] = np.array(f[key])
        if "timestamps" in f:
            result["timestamps"] = np.array(f["timestamps"])
        else:
            result["timestamps"] = np.arange(result["num_frames"]) * 0.05
        if "gripper" in f:
            result["gripper_states"] = np.array(f["gripper"])
        elif "actions" in f:
            actions = np.array(f["actions"])
            if actions.ndim > 1 and actions.shape[1] > 0:
                gripper = actions[:, -1].astype(float)
                g_min, g_max = gripper.min(), gripper.max()
                if g_max > g_min:
                    gripper = (gripper - g_min) / (g_max - g_min)
                result["gripper_states"] = gripper
            else:
                result["gripper_states"] = np.ones(result["num_frames"])
        else:
            result["gripper_states"] = np.ones(result["num_frames"])

        result["metadata"] = {
            "source": "hdf5",
            "path": path,
            "dataset_key": dataset_key,
            "hdf5_keys": list(f.keys()),
        }

    return result


def import_numpy(path: str) -> dict[str, Any]:
    """Import a trajectory from a NumPy .npz file.

    Expected keys in the .npz file:
    - actions: action array
    - states or observations: state array
    - timestamps (optional): time array
    - gripper (optional): gripper state array

    Args:
        path: Path to .npz file.

    Returns:
        Standardized episode dict.
    """
    data = np.load(path)

    result: dict[str, Any] = {
        "source_path": path,
    }

    if "actions" in data:
        result["actions"] = data["actions"]
        result["action_dim"] = result["actions"].shape[1] if result["actions"].ndim > 1 else 1
    else:
        result["actions"] = np.array([])
        result["action_dim"] = 0

    state_key = "states" if "states" in data else "observations" if "observations" in data else None
    if state_key:
        result["states"] = data[state_key]
        result["state_dim"] = result["states"].shape[1] if result["states"].ndim > 1 else 1
    else:
        result["states"] = np.array([])
        result["state_dim"] = 0

    if "timestamps" in data:
        result["timestamps"] = data["timestamps"]
    else:
        num_frames = len(result["actions"]) if result["actions"].size > 0 else 0
        result["timestamps"] = np.arange(num_frames) * 0.05

    if "gripper" in data:
        result["gripper_states"] = data["gripper"]
    elif result["actions"].size > 0 and result["actions"].ndim > 1:
        gripper = result["actions"][:, -1].astype(float)
        g_min, g_max = gripper.min(), gripper.max()
        if g_max > g_min:
            gripper = (gripper - g_min) / (g_max - g_min)
        result["gripper_states"] = gripper
    else:
        num_frames = len(result["actions"]) if result["actions"].size > 0 else 0
        result["gripper_states"] = np.ones(num_frames)

    result["num_frames"] = len(result["actions"]) if result["actions"].size > 0 else 0
    result["metadata"] = {
        "source": "numpy",
        "path": path,
        "keys": list(data.keys()),
    }

    return result
