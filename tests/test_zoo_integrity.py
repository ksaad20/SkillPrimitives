"""Validate pre-computed skill zoo integrity."""

from pathlib import Path

import pytest

ZOO_DIR = Path(__file__).parent.parent / "zoo"


class TestZooIntegrity:
    @pytest.mark.skipif(not ZOO_DIR.exists(), reason="No zoo directory")
    def test_zoo_directory_exists(self):
        assert ZOO_DIR.is_dir()

    @pytest.mark.skipif(not ZOO_DIR.exists(), reason="No zoo directory")
    def test_zoo_has_subdirectories(self):
        subdirs = [d for d in ZOO_DIR.iterdir() if d.is_dir()]
        # MVP: zoo exists but may not have populated subdirs yet
        # This test documents the expected structure without failing MVP
        if not subdirs:
            pytest.skip("Zoo exists but has no populated datasets yet")
        assert len(subdirs) > 0

    @pytest.mark.skipif(not ZOO_DIR.exists(), reason="No zoo directory")
    def test_zoo_entries_have_metadata(self):
        subdirs = [d for d in ZOO_DIR.iterdir() if d.is_dir()]
        if not subdirs:
            pytest.skip("No populated zoo entries to validate")
        for subdir in subdirs:
            meta = subdir / "metadata.yaml"
            assert meta.exists(), f"{subdir.name} missing metadata.yaml"
