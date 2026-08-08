"""Export primitives to various formats (JSON, Parquet, LeRobot)."""

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
        import pandas as pd  # type: ignore[import-untyped]

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
        import pandas as pd  # type: ignore[import-untyped]

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
        import pandas as pd  # type: ignore[import-untyped]

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
