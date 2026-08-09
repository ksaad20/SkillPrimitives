"""Tests for the skill composer."""

import pytest

from skill_primitives.core.composer import ComposedTask, SkillLibrary, compose


class TestComposer:
    def test_compose_returns_composed_task(self):
        task = compose(["reach the object", "grasp", "lift"])
        assert isinstance(task, ComposedTask)

    def test_compose_populates_primitives(self):
        task = compose(["reach the object", "grasp", "lift"])
        assert len(task.primitives) == 3

    def test_compose_maps_instructions_to_types(self):
        task = compose(["reach the object", "grasp firmly", "lift 5cm"])
        assert task.primitives[0]["type"] == "reach"
        assert task.primitives[1]["type"] == "grasp"
        assert task.primitives[2]["type"] == "lift"

    def test_compose_unknown_instruction_defaults_to_unknown(self):
        task = compose(["spin around", "jump up"])
        assert task.primitives[0]["type"] == "unknown"

    def test_composed_task_has_duration(self):
        task = compose(["reach", "grasp"])
        assert task.duration > 0

    def test_composed_task_exports_json(self, tmp_path):
        task = compose(["reach", "grasp"])
        out = tmp_path / "task.json"
        task.export_json(str(out))
        assert out.exists()
        data = json.loads(out.read_text())
        assert "task" in data
        assert data["task"]["num_primitives"] == 2
        assert isinstance(data["task"]["primitives"], list)

    def test_composed_task_export_lerobot(self, tmp_path):
        task = compose(["reach"])
        out = tmp_path / "task.parquet"
        task.export_lerobot(str(out))
        assert out.exists()

    def test_skill_library_from_disk_returns_empty_for_missing_path(self):
        lib = SkillLibrary.from_disk("/tmp/nonexistent_zoo_12345")
        assert isinstance(lib, SkillLibrary)
        assert lib.skills == []

    def test_skill_library_from_disk_loads_skills(self, tmp_path):
        import yaml

        zoo = tmp_path / "zoo"
        reach_dir = zoo / "reach"
        reach_dir.mkdir(parents=True)
        meta = {"description": "reach out"}
        (reach_dir / "metadata.yaml").write_text(yaml.safe_dump(meta))

        lib = SkillLibrary.from_disk(str(zoo))
        assert isinstance(lib, SkillLibrary)
        assert len(lib.skills) >= 1
        assert any(s.skill_type == "reach" for s in lib.skills)
