"""Tests for data exporters."""

import json

import pytest

from skill_primitives.io.exporters import JSONExporter, ParquetExporter


class TestJSONExporter:
    def test_export_creates_file(self, tmp_path):
        exp = JSONExporter()
        out = tmp_path / "test.json"
        exp.export({"primitives": [{"type": "reach"}]}, str(out))
        assert out.exists()

    def test_export_content_is_valid_json(self, tmp_path):
        exp = JSONExporter()
        out = tmp_path / "test.json"
        exp.export({"primitives": [{"type": "reach"}, {"type": "grasp"}]}, str(out))
        data = json.loads(out.read_text())
        assert isinstance(data, list)
        assert data[0]["type"] == "reach"


class TestParquetExporter:
    def test_export_creates_file(self, tmp_path):
        pytest.importorskip("pandas")
        pytest.importorskip("pyarrow")
        exp = ParquetExporter()
        out = tmp_path / "test.parquet"
        exp.export({"primitives": [{"type": "reach"}, {"type": "grasp"}]}, str(out))
        assert out.exists()

    def test_export_without_pyarrow_raises(self, tmp_path, monkeypatch):
        """Ensure graceful failure if pyarrow is missing."""
        import sys

        # Temporarily hide pandas/pyarrow
        modules_to_hide = ["pandas", "pyarrow"]
        for mod in modules_to_hide:
            monkeypatch.setitem(sys.modules, mod, None)

        # Re-import to get fresh state
        from skill_primitives.io.exporters import ParquetExporter

        exp = ParquetExporter()
        out = tmp_path / "test.parquet"
        # Should raise ImportError when trying to import pandas
        with pytest.raises((ImportError, ModuleNotFoundError)):
            exp.export({"primitives": [{"type": "reach"}]}, str(out))
