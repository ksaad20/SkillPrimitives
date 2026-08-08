import json
from pathlib import Path
from typing import Any

import numpy as np


class BaseExporter:
    """Base class for all exporters."""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, primitives: list[dict[str, Any]], path: str) -> None:
        raise NotImplementedError


class JSONExporter(BaseExporter):
    """Export primitives to JSON."""

    def export(self, primitives: list[dict[str, Any]], path: str) -> None:
        full_path = self.output_dir / path
        with open(full_path, "w") as f:
            json.dump(primitives, f, indent=2)
        print(f"Exported {len(primitives)} primitives to {full_path}")


class ParquetExporter(BaseExporter):
    """Export primitives to Parquet via pandas."""

    def export(self, primitives: list[dict[str, Any]], path: str) -> None:
        import pandas as pd

        full_path = self.output_dir / path

        if not primitives:
            df = pd.DataFrame(columns=["type", "start", "end", "confidence", "description"])
        else:
            records = []
            for p in primitives:
                records.append(
                    {
                        "type": p.get("type", ""),
                        "start": p.get("start", 0),
                        "end": p.get("end", 0),
                        "confidence": p.get("confidence", 0.0),
                        "description": p.get("description", ""),
                    }
                )
            df = pd.DataFrame(records)

        df.to_parquet(full_path, index=False)
        print(f"Exported {len(primitives)} primitives to {full_path}")

    def export_batch(self, tasks: list[dict[str, Any]], path: str) -> None:
        import pandas as pd

        records = []
        for task_idx, task in enumerate(tasks):
            for p in task.get("primitives", []):
                records.append(
                    {
                        "task_index": task_idx,
                        "type": p.get("type", ""),
                        "start": p.get("start", 0),
                        "end": p.get("end", 0),
                        "confidence": p.get("confidence", 0.0),
                        "description": p.get("description", ""),
                    }
                )

        df = pd.DataFrame(records)
        df.to_parquet(self.output_dir / path, index=False)
        print(f"Exported batch of {len(tasks)} tasks to {self.output_dir / path}")


class LeRobotExporter(BaseExporter):
    """Export primitives in LeRobot-compatible Parquet format."""

    def __init__(self, output_dir: str, fps: float = 20.0):
        super().__init__(output_dir)
        self.fps = fps
        self.dt = 1.0 / fps

    def _generate_action(self, ptype: str, frame: int, total: int) -> list[float]:
        """Generate a plausible action vector for a frame."""
        t = frame / max(total, 1)
        if ptype == "reach":
            return [0.5 * (1 - t), 0.3 * t, 0.1, 0.0, 0.0, 0.0, 1.0]
        elif ptype == "grasp":
            grip = 0.5 + 0.5 * np.sin(np.pi * t)
            return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, grip]
        elif ptype == "lift":
            return [0.0, 0.0, 0.3 * t, 0.0, 0.0, 0.0, 1.0]
        elif ptype == "place":
            return [0.2 * (1 - t), 0.2 * (1 - t), -0.1 * t, 0.0, 0.0, 0.0, 1.0 - t]
        return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    def _generate_state(self, ptype: str, frame: int, total: int) -> list[float]:
        """Generate a plausible state vector for a frame."""
        t = frame / max(total, 1)
        base = [0.3 + 0.2 * t, -0.1 + 0.3 * t, 0.15 + 0.1 * np.sin(2 * np.pi * t)]
        if ptype == "grasp":
            base.append(0.5 + 0.5 * np.sin(np.pi * t))
        else:
            base.append(1.0)
        return base

    def export(
        self,
        primitives: list[dict[str, Any]],
        path: str,
        episode_idx: int = 0,
    ) -> None:
        import pandas as pd

        rows = []
        global_frame = 0

        for p in primitives:
            ptype = p.get("type", "unknown")
            num_frames = p.get("end", 10) - p.get("start", 0)

            for i in range(num_frames):
                action = self._generate_action(ptype, i, num_frames)
                state = self._generate_state(ptype, i, num_frames)

                rows.append(
                    {
                        "timestamp": global_frame * 0.05,
                        "frame_index": global_frame,
                        "episode_index": episode_idx,
                        "action": action,
                        "observation.state": state,
                    }
                )
                global_frame += 1

        df = pd.DataFrame(rows)
        df.to_parquet(self.output_dir / path, index=False)
        print(f"Exported LeRobot format to {self.output_dir / path}")

    def export_policy(self, primitives: list[dict[str, Any]], path: str) -> None:
        """Export as a policy script."""
        lines = [
            "# Auto-generated policy from skill primitives",
            "class AutoPolicy:",
            "    def __init__(self):",
            "        self.primitives = []",
            "",
            "    def execute_task(self):",
        ]

        for i, p in enumerate(primitives):
            desc = p.get("description", p.get("type", "unknown"))
            lines.append(f'        self.publish_skill({i}, "{desc}")')

        lines.extend(
            [
                "",
                "    def publish_skill(self, idx, desc):",
                '        print(f"Executing skill {idx}: {desc}")',
                "",
            ]
        )

        full_path = self.output_dir / path
        full_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Exported policy to {full_path}")


"""ROS2 trajectory exporter."""


class ROS2Exporter:
    """Export robot trajectories to ROS2-compatible CSV + YAML.

    Writes joint-state CSV logs and ROS2 parameter YAML sidecars
    that integrate with ``ros2 bag play`` and ``ros2 launch``.

    Output structure:
    ::

        output_dir/
          {filename}_trajectory.csv   # time_sec, joint_0, joint_1, ...
          {filename}_metadata.yaml    # ros__parameters block

    Args:
        output_dir: Destination directory. Created if missing.
        joint_names: Ordered list of joint names. If ``None``, generic
            ``joint_0``, ``joint_1``, ... names are used.
        frame_id: TF frame_id for the trajectory (default: ``"base_link"``).
    """

    def __init__(
        self,
        output_dir: str | Path,
        joint_names: list[str] | None = None,
        frame_id: str = "base_link",
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.joint_names = list(joint_names) if joint_names else []
        self.frame_id = frame_id

    def export(
        self,
        trajectory: dict[str, Any],
        filename: str,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """Export a trajectory to ROS2-compatible files.

        Args:
            trajectory: Must contain one of ``states``, ``actions``,
                ``observations``, or ``state``. Values should be array-like
                with shape ``(T, D)`` where ``T`` is timesteps and ``D``
                is state dimensionality.
            filename: Base name for output files (no extension).
            metadata: Optional metadata embedded in the YAML sidecar.

        Returns:
            Path to the written YAML metadata file.
        """
        states = self._extract_states(trajectory)
        timestamps = self._extract_timestamps(trajectory, len(states))

        csv_path = self._write_csv(filename, timestamps, states)
        yaml_path = self._write_yaml(filename, csv_path, metadata)

        return yaml_path

    def _extract_states(self, trajectory: dict[str, Any]) -> np.ndarray:
        """Extract state array from trajectory dict."""
        raise ValueError(
            "Trajectory must contain one of: states, actions, observations, state"
        )

    def _extract_timestamps(
        self, trajectory: dict[str, Any], num_frames: int
    ) -> np.ndarray:
        """Build a timestamp array if not present."""
        if "timestamps" in trajectory:
            ts = trajectory["timestamps"]
            return ts if isinstance(ts, np.ndarray) else np.asarray(ts)
        # Default: assume 30 Hz
        return np.arange(num_frames) / 30.0

    def _write_csv(self, filename: str, timestamps: np.ndarray, states: np.ndarray
    ) -> Path:

        csv_path = self.output_dir / (filename + "_trajectory.csv")
        yaml_path = self.output_dir / (filename + "_metadata.yaml")

        header = ["time_sec"]
        if self.joint_names and len(self.joint_names) == states.shape[-1]:
            header.extend(self.joint_names)
        else:
            header.extend(f"joint_{i}" for i in range(states.shape[-1]))

        rows = np.column_stack([timestamps, states.reshape(len(timestamps), -1)])
        np.savetxt(csv_path, rows, delimiter=",", header=",".join(header), comments="")

        return csv_path

    def _write_yaml(
        self,
        filename: str,
        csv_path: Path,
        metadata: dict[str, Any] | None,
    ) -> Path:
        """Write ROS2 parameter YAML sidecar."""
        yaml_path = self.output_dir / f"{filename}_metadata.yaml"

        payload = {
            "ros__parameters": {
                "trajectory_file": str(csv_path.resolve()),
                "frame_id": self.frame_id,
                "joint_names": self.joint_names,
                "rate_hz": 30.0,
                "metadata": metadata or {},
            }
        }

        lines = ["# ROS2 parameter file generated by SkillPrimitives", ""]
        lines.extend(self._dict_to_yaml(payload))
        yaml_path.write_text("\n".join(lines))

        return yaml_path

    @staticmethod
    def _dict_to_yaml(data: dict[str, Any], indent: int = 0) -> list[str]:
        """Recursively serialize a dict to YAML lines."""
        lines: list[str] = []
        prefix = "  " * indent
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.extend(ROS2Exporter._dict_to_yaml(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}:")
                for item in value:
                    lines.append(f"{prefix}  - {item}")
            elif isinstance(value, str):
                lines.append(f'{prefix}{key}: "{value}"')
            else:
                lines.append(f"{prefix}{key}: {value}")
        return lines
