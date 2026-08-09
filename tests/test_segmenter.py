"""Tests for the trajectory segmenter."""

from skill_primitives.core.segmenter import Segmenter
import numpy as np
import pytest


class TestSegmenter:
    def _make_synthetic_episode(self) -> dict:
        """Create a synthetic episode with clear gripper transitions."""
        num_frames = 100
        actions = np.zeros((num_frames, 8))
        # Gripper open (1.0) -> closed (0.0) at frame 20 (grasp)
        actions[:20, -1] = 1.0
        actions[20:60, -1] = 0.0
        # Gripper closed -> open at frame 60 (place)
        actions[60:, -1] = 1.0

        # State: xyz position
        state = np.zeros((num_frames, 10))
        # Reach: moving toward target before grasp
        state[:20, :3] = np.linspace([0, 0, 0], [1, 1, 0.5], 20)
        # Lift: positive z after grasp
        state[20:40, :3] = np.linspace([1, 1, 0.5], [1, 1, 1.0], 20)
        # Transport: xy movement
        state[40:60, :3] = np.linspace([1, 1, 1.0], [2, 2, 1.0], 20)
        # Place: lowering z
        state[60:80, :3] = np.linspace([2, 2, 1.0], [2, 2, 0.5], 20)

        return {"actions": actions, "state": state}

    def test_segment_returns_list(self):
        segmenter = Segmenter()
        episode = self._make_synthetic_episode()
        result = segmenter.segment(episode)
        assert isinstance(result, list)

    def test_segment_has_required_keys(self):
        segmenter = Segmenter()
        episode = self._make_synthetic_episode()
        result = segmenter.segment(episode)
        required = {"type", "start", "end", "confidence"}
        for seg in result:
            assert required.issubset(seg.keys()), f"Missing keys in {seg}"

    def test_segment_types_are_known(self):
        known = {"reach", "grasp", "lift", "transport", "place"}
        segmenter = Segmenter()
        episode = self._make_synthetic_episode()
        result = segmenter.segment(episode)
        for seg in result:
            assert seg["type"] in known, f"Unknown type: {seg['type']}"

    def test_segment_frame_ranges_are_valid(self):
        segmenter = Segmenter()
        episode = self._make_synthetic_episode()
        result = segmenter.segment(episode)
        for seg in result:
            assert seg["start"] < seg["end"], f"Invalid range: {seg['start']}-{seg['end']}"
            assert 0 <= seg["confidence"] <= 1, f"Invalid confidence: {seg['confidence']}"

    def test_segment_empty_actions(self):
        segmenter = Segmenter()
        episode = {"actions": np.array([]), "state": np.array([])}
        result = segmenter.segment(episode)
        assert result == []

    def test_load_lerobot_episode_requires_revision(self):
        with pytest.raises(TypeError):
            Segmenter.load_lerobot_episode("lerobot/pusht", episode=0)
