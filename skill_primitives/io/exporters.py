"""Export composed tasks to various formats.

Supports JSON (human-readable), Parquet (columnar), and
LeRobot-compatible Parquet (training pipeline input).
"""

from __future__ import annotations

import json
from typing import Any

from skill_primitives.io.base import BaseExporter


class JSONExporter(BaseExporter):
    """Export composed tasks to JSON.

    Human-readable format suitable for inspection, version control,
    and interoperability with non-Python tools.
    """

    def export(self, task: dict[str, Any], path: str) -> None:
        """Export a composed task to JSON.

        Args:
            task: Task dict with at least a 'primitives' key.
            path: Output file path.
        """
        with open(path, "w") as f:
            json.dump(task, f, indent=2, default=str)

    def export_batch(self, tasks: list[dict[str, Any]], path: str) -> None:
        """Export multiple tasks to a single JSON array file."""
        with open(path, "w") as f:
            json.dump(tasks, f, indent=2, default=str)


class ParquetExporter(BaseExporter):
    """Export composed tasks to Apache Parquet.

    Efficient columnar format for large datasets and ML pipelines.
    Requires pandas and pyarrow.
    """

    def export(self, task: dict[str, Any], path: str) -> None:
        """Export a composed task to Parquet.

        Flattens primitives into a DataFrame with one row per primitive.
        """
        import pandas as pd

        primitives = task.get("primitives", [])
        if not primitives:
            df = pd.DataFrame(columns=["type", "start", "end", "confidence", "description"])
        else:
            records = []
            for p in primitives:
                records.append({
                    "type": p.get("type", ""),
                    "start": p.get("start", 0),
                    "end": p.get("end", 0),
                    "confidence": p.get("confidence", 0.0),
                    "description": p.get("description", ""),
                })
            df = pd.DataFrame(records)

        df.to_parquet(path, index=False)

    def export_batch(self, tasks: list[dict[str, Any]], path: str) -> None:
        """Export multiple tasks to a single Parquet file."""
        import pandas as pd

        records = []
        for task_idx, task in enumerate(tasks):
            for p in task.get("primitives", []):
                records.append({
                    "task_index": task_idx,
                    "type": p.get("type", ""),
                    "start": p.get("start", 0),
                    "end": p.get("end", 0),
                    "confidence": p.get("confidence", 0.0),
                    "description": p.get("description", ""),
                })

        df = pd.DataFrame(records)
        df.to_parquet(path, index=False)


class LeRobotExporter(BaseExporter):
    """Export composed tasks to LeRobot-compatible Parquet format.

    Produces files with the exact schema expected by LeRobot training:
    - timestamp
    - frame_index
    - episode_index
    - action
    - observation.state
    - observation.image (optional)
    """

    def export(self, task: dict[str, Any], path: str) -> None:
        """Export a composed task to LeRobot Parquet.

        Generates synthetic trajectory frames from composed primitives.
        """
        import pandas as pd
        import numpy as np

        primitives = task.get("primitives", [])
        episode_idx = task.get("episode_index", 0)

        rows = []
        global_frame = 0

        for primitive in primitives:
            ptype = primitive.get("type", "unknown")
            num_frames = primitive.get("end", 10) - primitive.get("start", 0)
            num_frames = max(num_frames, 5)  # Minimum 5 frames per primitive

            for i in range(num_frames):
                # Generate plausible action based on primitive type
                action = self._generate_action(ptype, i, num_frames)
                state = self._generate_state(ptype, i, num_frames)

                rows.append({
                    "timestamp": global_frame * 0.05,
                    "frame_index": global_frame,
                    "episode_index": episode_idx,
                    "action": action,
                    "observation.state": state,
                })
                global_frame += 1

        df = pd.DataFrame(rows)
        df.to_parquet(path, index=False)

    def _generate_action(self, ptype: str, frame: int, total: int) -> list[float]:
        """Generate a plausible action vector for a primitive type."""
        import numpy as np

        # Standard 7-DOF action: [x, y, z, rx, ry, rz, gripper]
        action = [0.0] * 7

        t = frame / max(total - 1, 1)  # Normalized time [0, 1]

        if ptype == "reach":
            action[0] = t * 0.1  # Move forward
            action[1] = t * 0.05  # Slight lateral
            action[6] = 1.0  # Gripper open
        elif ptype == "grasp":
            action[6] = 1.0 - t  # Close gripper
        elif ptype == "lift":
            action[2] = t * 0.05  # Move up
            action[6] = 0.0  # Gripper closed
        elif ptype == "transport":
            action[0] = t * 0.1  # Move horizontally
            action[6] = 0.0  # Gripper closed
        elif ptype == "place":
            action[2] = -t * 0.05  # Move down
            action[6] = t  # Open gripper

        return action

    def _generate_state(self, ptype: str, frame: int, total: int) -> list[float]:
        """Generate a plausible state vector for a primitive type."""
        # Simplified: state mirrors action for MVP
        return self._generate_action(ptype, frame, total)


class ROS2Exporter(BaseExporter):
    """Export composed tasks to ROS2-compatible format.

    Generates a Python script that publishes the task as ROS2 actions.
    """

    def export(self, task: dict[str, Any], path: str) -> None:
        """Export a composed task as a ROS2 Python script.

        Creates a self-contained script that uses rclpy to execute
        the composed task on a ROS2 robot.
        """
        primitives = task.get("primitives", [])

        lines = [
            "#!/usr/bin/env python3",
            '"""Auto-generated ROS2 task script."""',
            "",
            "import rclpy",
            "from rclpy.node import Node",
            "from std_msgs.msg import String",
            "",
            "class SkillPrimitiveExecutor(Node):",
            "    def __init__(self):",
            '        super().__init__("skill_primitive_executor")',
            '        self.publisher = self.create_publisher(String, "skill_command", 10)',
            "",
            "    def execute_task(self):",
        ]

        for i, p in enumerate(primitives):
            desc = p.get("description", p.get("type", "unknown"))
            lines.append(f'        self.publish_skill({i}, "{desc}")')

        lines.extend([
            "",
            "    def publish_skill(self, index, description):",
            '        msg = String()',
            '        msg.data = f"{{index}}: {{description}}"',
            "        self.publisher.publish(msg)",
            '        self.get_logger().info(f"Published: {{msg.data}}")',
            "",
            "def main(args=None):",
            "    rclpy.init(args=args)",
            "    executor = SkillPrimitiveExecutor()",
            "    executor.execute_task()",
            "    executor.destroy_node()",
            "    rclpy.shutdown()",
            "",
            'if __name__ == "__main__":',
            "    main()",
            "",
        ])

        with open(path, "w") as f:
            f.write("
".join(lines))


def get_exporter(format_name: str) -> BaseExporter:
    """Factory: get an exporter by format name.

    Args:
        format_name: One of "json", "parquet", "lerobot", "ros2".

    Returns:
        Exporter instance.

    Raises:
        ValueError: If format is not supported.
    """
    exporters = {
        "json": JSONExporter,
        "parquet": ParquetExporter,
        "lerobot": LeRobotExporter,
        "ros2": ROS2Exporter,
    }

    if format_name.lower() not in exporters:
        available = ", ".join(exporters.keys())
        raise ValueError(f"Unknown format: '{format_name}'. Available: {available}")

    return exporters[format_name.lower()]()
