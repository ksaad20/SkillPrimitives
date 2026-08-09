"""Tests for data exporters."""

import json

import numpy as np
import pytest

from skill_primitives.io.exporters import (
    Exporter,
    JSONExporter,
    ROS2Exporter,
    get_exporter,
    register_exporter,
)


class TestJSONExporter:
    def test_export_creates_json_file(self, tmp_path):
        exp = JSONExporter(tmp_path)
        result = exp.export({"primitives": [{"type": "reach"}]}, "test")
        assert result.exists()
        assert result == tmp_path / "test.json"

    def test_export_content_is_valid_json(self, tmp_path):
        exp = JSONExporter(tmp_path)
        result = exp.export(
            {"primitives": [{"type": "reach"}, {"type": "grasp"}]},
            "test",
            metadata={"author": "test"},
        )
        data = json.loads(result.read_text())
        assert data["metadata"] == {"author": "test"}
        assert data["primitives"] == [{"type": "reach"}, {"type": "grasp"}]

    def test_export_converts_numpy_to_list(self, tmp_path):
        exp = JSONExporter(tmp_path)
        result = exp.export(
            {"states": np.array([[1.0, 2.0], [3.0, 4.0]])},
            "test",
        )
        data = json.loads(result.read_text())
        assert data["states"] == [[1.0, 2.0], [3.0, 4.0]]

    def test_export_converts_sequence_to_list(self, tmp_path):
        exp = JSONExporter(tmp_path)
        result = exp.export(
            {"items": (1, 2, 3)},
            "test",
        )
        data = json.loads(result.read_text())
        assert data["items"] == [1, 2, 3]

    def test_export_leaves_string_intact(self, tmp_path):
        exp = JSONExporter(tmp_path)
        result = exp.export(
            {"label": "reach"},
            "test",
        )
        data = json.loads(result.read_text())
        assert data["label"] == "reach"

    def test_export_without_metadata(self, tmp_path):
        exp = JSONExporter(tmp_path)
        result = exp.export({"primitives": []}, "empty")
        data = json.loads(result.read_text())
        assert data["metadata"] == {}


class TestROS2Exporter:
    def test_export_creates_csv_and_yaml(self, tmp_path):
        exp = ROS2Exporter(tmp_path, joint_names=["j1", "j2"])
        trajectory = {
            "states": np.array([[0.0, 0.0], [1.0, 2.0]]),
        }
        result = exp.export(trajectory, "motion", metadata={"task": "pick"})

        assert result.exists()
        assert result == tmp_path / "motion_metadata.yaml"
        assert (tmp_path / "motion_trajectory.csv").exists()

    def test_export_yaml_content(self, tmp_path):
        exp = ROS2Exporter(tmp_path, joint_names=["j1", "j2"], frame_id="world")
        trajectory = {
            "states": np.array([[0.0, 0.0], [1.0, 2.0]]),
            "timestamps": np.array([0.0, 1.0]),
        }
        result = exp.export(trajectory, "motion")

        yaml_text = result.read_text()
        assert "world" in yaml_text
        assert "motion_trajectory.csv" in yaml_text
        assert "j1" in yaml_text
        assert "j2" in yaml_text
        assert "ros__parameters" in yaml_text

    def test_export_csv_content(self, tmp_path):
        exp = ROS2Exporter(tmp_path, joint_names=["j1", "j2"])
        trajectory = {
            "states": np.array([[0.0, 0.0], [1.0, 2.0]]),
            "timestamps": np.array([0.0, 1.0]),
        }
        exp.export(trajectory, "motion")

        csv_text = (tmp_path / "motion_trajectory.csv").read_text()
        assert "time_sec" in csv_text
        assert "j1" in csv_text
        assert "j2" in csv_text

    def test_export_without_joint_names_uses_defaults(self, tmp_path):
        exp = ROS2Exporter(tmp_path)
        trajectory = {
            "states": np.array([[0.0, 0.0], [1.0, 2.0]]),
        }
        exp.export(trajectory, "motion")

        csv_text = (tmp_path / "motion_trajectory.csv").read_text()
        assert "joint_0" in csv_text
        assert "joint_1" in csv_text

    def test_export_without_states_raises(self, tmp_path):
        exp = ROS2Exporter(tmp_path)
        with pytest.raises(ValueError, match="Trajectory must contain one of"):
            exp.export({"primitives": [{"type": "reach"}]}, "test")

    def test_default_timestamps(self, tmp_path):
        exp = ROS2Exporter(tmp_path, joint_names=["j1"])
        trajectory = {
            "states": np.array([[0.0], [1.0], [2.0]]),
        }
        exp.export(trajectory, "motion")

        csv_path = tmp_path / "motion_trajectory.csv"
        assert csv_path.exists()
        csv_text = csv_path.read_text()
        assert "0" in csv_text

    def test_default_frame_id(self, tmp_path):
        exp = ROS2Exporter(tmp_path)
        trajectory = {
            "states": np.array([[0.0]]),
        }
        result = exp.export(trajectory, "motion")
        yaml_text = result.read_text()
        assert "base_link" in yaml_text


class TestExporterRegistry:
    def test_get_exporter_json(self):
        assert get_exporter("json") is JSONExporter

    def test_get_exporter_ros2(self):
        assert get_exporter("ros2") is ROS2Exporter

    def test_get_exporter_case_insensitive(self):
        assert get_exporter("JSON") is JSONExporter
        assert get_exporter("Ros2") is ROS2Exporter
        assert get_exporter("  json  ") is JSONExporter

    def test_get_exporter_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown exporter"):
            get_exporter("unknown")

    def test_register_exporter(self, tmp_path, monkeypatch):
        from skill_primitives.io import exporters as exporters_mod

        monkeypatch.setattr(
            exporters_mod, "_EXPORTERS", dict(exporters_mod._EXPORTERS)
        )

        class DummyExporter(Exporter):
            def export(self, trajectory, filename, metadata=None):
                path = tmp_path / (filename + ".dummy")
                path.write_text("dummy")
                return path

        register_exporter("dummy", DummyExporter)
        assert get_exporter("dummy") is DummyExporter
