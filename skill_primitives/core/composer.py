from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Skill:
    def __init__(
        self,
        skill_type: str,
        description: str,
        trajectory: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.skill_type = skill_type
        self.description = description
        self.trajectory = trajectory or {}
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        return f"Skill({self.skill_type}: {self.description})"


class SkillLibrary:
    """Disk-based library of segmented and annotated skills.

    Directory structure:
        library_root/
        ├── reach/
        │   ├── episode_000_seg_001.parquet
        │   └── metadata.yaml
        ├── grasp/
        └── ...
    """

    def __init__(self, skills: list[Skill]) -> None:
        self.skills = skills
        self._by_type: dict[str, list[Skill]] = {}
        self._index_by_type()

    def _index_by_type(self) -> None:
        """Index skills by type for fast lookup."""
        self._by_type = {}
        for skill in self.skills:
            self._by_type.setdefault(skill.skill_type, []).append(skill)

    @classmethod
    def from_disk(cls, path: str) -> SkillLibrary:
        """Load a skill library from a directory structure.

        Args:
            path: Root directory containing primitive subfolders.

        Returns:
            A SkillLibrary with all loaded skills.
        """
        lib_path = Path(path)
        if not lib_path.exists():
            # Return empty library for non-existent paths
            return cls([])

        skills = []
        known_types = ["reach", "grasp", "lift", "transport", "place"]

        for ptype in known_types:
            type_dir = lib_path / ptype
            if not type_dir.exists():
                continue

            # Load metadata.yaml files
            for meta_file in sorted(type_dir.glob("**/metadata.yaml")):
                try:
                    import yaml

                    metadata = yaml.safe_load(meta_file.read_text()) or {}
                except Exception:
                    metadata = {}

                description = metadata.get("description", f"perform {ptype}")

                # Try to load corresponding parquet trajectory
                traj_file = meta_file.with_suffix(".parquet")
                if not traj_file.exists():
                    traj_file = meta_file.parent / (
                        meta_file.stem.replace("_metadata", "") + ".parquet"
                    )

                trajectory: dict[str, Any] = {}
                if traj_file.exists():
                    try:
                        import pandas as pd

                        df = pd.read_parquet(traj_file)
                        trajectory = {"data": df.to_dict("records")}
                    except Exception:
                        trajectory = {}

                skills.append(
                    Skill(
                        skill_type=ptype,
                        description=description,
                        trajectory=trajectory,
                        metadata=metadata,
                    )
                )

        return cls(skills)

    def get_by_type(self, skill_type: str) -> list[Skill]:
        """Get all skills of a given type."""
        return self._by_type.get(skill_type, [])

    def find_best_match(self, instruction: str) -> Skill | None:
        """Find the best matching skill for a natural language instruction.

        Uses keyword extraction first, then falls back to description similarity.

        Args:
            instruction: Natural language command.

        Returns:
            Best matching Skill, or None if no match found.
        """
        instruction_lower = instruction.lower()

        # Step 1: Keyword extraction for primitive type
        type_keywords = {
            "reach": ["reach", "approach", "move toward", "extend to"],
            "grasp": ["grasp", "grab", "grip", "hold", "pick up", "secure"],
            "lift": ["lift", "raise", "elevate", "hoist", "pick up"],
            "transport": ["transport", "move", "carry", "transfer", "convey"],
            "place": ["place", "put", "set down", "deposit", "release", "drop"],
        }

        detected_type: str | None = None
        best_score = 0

        for ptype, keywords in type_keywords.items():
            score = sum(1 for kw in keywords if kw in instruction_lower)
            if score > best_score:
                best_score = score
                detected_type = ptype

        if detected_type is None:
            return None

        candidates = self.get_by_type(detected_type)
        if not candidates:
            return None

        # Step 2: Among candidates of the right type, pick by description similarity
        best_skill = candidates[0]
        best_desc_score = 0

        for skill in candidates:
            desc_lower = skill.description.lower()
            # Simple word overlap score
            instr_words = set(instruction_lower.split())
            desc_words = set(desc_lower.split())
            overlap = len(instr_words & desc_words)
            if overlap > best_desc_score:
                best_desc_score = overlap
                best_skill = skill

        return best_skill


class ComposedTask:
    """A sequence of composed primitives ready for export or execution."""

    def __init__(self, skills: list[Skill]) -> None:
        self.skills = skills

    @property
    def primitives(self) -> list[dict[str, Any]]:
        """Return primitives as dicts for backward compatibility."""
        return [
            {
                "type": s.skill_type,
                "instruction": s.description,
                "metadata": s.metadata,
            }
            for s in self.skills
        ]

    @property
    def duration(self) -> float:
        """Estimated duration in seconds (2.5s per primitive as heuristic)."""
        return len(self.skills) * 2.5

    def export_json(self, path: str) -> None:
        """Export composed task to JSON.

        Args:
            path: Output file path.
        """
        data = {
            "task": {
                "num_primitives": len(self.skills),
                "estimated_duration": self.duration,
                "primitives": self.primitives,
            }
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def export_lerobot(self, path: str) -> None:
        """Export composed task to LeRobot Parquet format.

        Creates a Parquet file with the standard LeRobot episode schema:
        - timestamp
        - frame_index
        - episode_index
        - action
        - observation.state

        Args:
            path: Output file path (should end in .parquet).
        """
        try:
            import pandas as pd
        except ImportError as err:
            raise ImportError(
                "pandas is required for LeRobot export. " "Install with: pip install pandas"
            ) from err

        rows = []
        global_frame = 0
        episode_idx = 0

        for skill in self.skills:
            # If skill has trajectory data, use it
            if skill.trajectory and "data" in skill.trajectory:
                traj_data = skill.trajectory["data"]
                for _i, frame in enumerate(traj_data):
                    rows.append(
                        {
                            "timestamp": global_frame * 0.05,
                            "frame_index": global_frame,
                            "episode_index": episode_idx,
                            "action": frame.get("action", [0.0] * 7),
                            "observation.state": frame.get("state", [0.0] * 7),
                        }
                    )
                    global_frame += 1
            else:
                # Generate synthetic frames for skills without trajectory data
                num_frames = 10
                for _i in range(num_frames):
                    rows.append(
                        {
                            "timestamp": global_frame * 0.05,
                            "frame_index": global_frame,
                            "episode_index": episode_idx,
                            "action": [0.0] * 7,
                            "observation.state": [0.0] * 7,
                        }
                    )
                    global_frame += 1

        df = pd.DataFrame(rows)
        df.to_parquet(path, index=False)


def compose(
    instructions: list[str],
    library: SkillLibrary | None = None,
) -> ComposedTask:
    """Compose a task sequence from natural language instructions.

    Matches each instruction against the skill library and chains
    the best-matching skills into a composed task.

    Args:
        instructions: List of natural language commands.
        library: Optional skill library for lookup. If None, creates
            placeholder skills from instruction keywords.

    Returns:
        A ComposedTask ready for export or execution.
    """
    skills: list[Skill] = []

    for instruction in instructions:
        if library is not None:
            skill = library.find_best_match(instruction)
            if skill is not None:
                skills.append(skill)
                continue

        # Fallback: create a placeholder skill from instruction keywords
        ptype = "unknown"
        for key in ["reach", "grasp", "lift", "transport", "place"]:
            if key in instruction.lower():
                ptype = key
                break

        skills.append(
            Skill(
                skill_type=ptype,
                description=instruction,
            )
        )

    return ComposedTask(skills)
