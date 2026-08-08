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
        assert out.read_text().startswith("[")

    def test_composed_task_export_lerobot_is_stub(self):
        task = compose(["reach"])
        with pytest.raises(NotImplementedError):
            task.export_lerobot("/tmp/fake.parquet")

    def test_skill_library_from_disk_returns_valid_library(self):
        lib = SkillLibrary.from_disk("/tmp/fake_zoo")
        assert isinstance(lib, SkillLibrary)
        assert "reach" in lib.skills
        assert "grasp" in lib.skills
        assert "lift" in lib.skills
        assert "place" in lib.skills
