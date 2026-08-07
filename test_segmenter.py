"""Tests for the trajectory segmenter."""

import pytest

from skill_primitives.core.segmenter import segment_episode


class TestSegmenter:
    def test_segment_episode_returns_list(self):
        result = segment_episode("lerobot/pusht", episode=0)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_segment_episode_has_required_keys(self):
        result = segment_episode("lerobot/pusht", episode=0)
        required = {"type", "start", "end", "confidence"}
        for seg in result:
            assert required.issubset(seg.keys()), f"Missing keys in {seg}"

    def test_segment_episode_types_are_known(self):
        known = {"reach", "grasp", "lift", "transport", "place"}
        result = segment_episode("lerobot/pusht", episode=0)
        for seg in result:
            assert seg["type"] in known, f"Unknown type: {seg['type']}"

    def test_segment_episode_frame_ranges_are_valid(self):
        result = segment_episode("lerobot/pusht", episode=0)
        for seg in result:
            assert seg["start"] < seg["end"], f"Invalid range: {seg['start']}-{seg['end']}"
            assert 0 <= seg["confidence"] <= 1, f"Invalid confidence: {seg['confidence']}"
