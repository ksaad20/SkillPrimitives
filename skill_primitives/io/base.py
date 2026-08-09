"""Abstract base classes for dataset adapters and exporters.

Provides the interface contract for:
- Loading robot trajectory datasets from various sources
- Exporting composed tasks to various formats
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseAdapter(ABC):
    """Adapter for loading robot trajectory datasets.

    Subclasses implement loading logic for specific dataset formats
    (LeRobot, ROS bags, CSV, HDF5, etc.).
    """

    @abstractmethod
    def load_episode(
        self, dataset_path: str, episode_index: int = 0, *, revision: str
    ) -> dict[str, Any]:
        """Load a single episode as a standardized dict.

        Args:
            dataset_path: Path or identifier for the dataset.
            episode_index: Episode index to load.
            revision: Specific git revision (commit hash or tag) to pin
                the dataset version. Required for reproducibility.

        Returns:
            Standardized episode dict with keys:
            - observations: list or array of observations
            - actions: list or array of actions
            - states: list or array of state vectors (optional)
            - timestamps: list or array of timestamps (optional)
            - gripper_states: list or array of gripper values (optional)
            - images: list of image paths or arrays (optional)
            - metadata: episode-level metadata dict (optional)
        """
        ...

    @abstractmethod
    def list_episodes(self, dataset_path: str, *, revision: str) -> list[int]:
        """Return a list of available episode indices.

        Args:
            dataset_path: Path or identifier for the dataset.
            revision: Specific git revision (commit hash or tag) to pin
                the dataset version. Required for reproducibility.

        Returns:
            List of episode index integers.
        """
        ...

    def load_all_episodes(
        self, dataset_path: str, *, revision: str
    ) -> list[dict[str, Any]]:
        """Load all episodes from a dataset.

        Convenience method that calls load_episode for each available index.

        Args:
            dataset_path: Path or identifier for the dataset.
            revision: Specific git revision (commit hash or tag) to pin
                the dataset version. Required for reproducibility.

        Returns:
            List of episode dicts.
        """
        indices = self.list_episodes(dataset_path, revision=revision)
        return [self.load_episode(dataset_path, idx, revision=revision) for idx in indices]


class BaseExporter(ABC):
    """Exporter for composed task sequences.

    Subclasses implement export logic for specific formats
    (JSON, Parquet, LeRobot, ROS2, etc.).
    """

    @abstractmethod
    def export(self, task: dict[str, Any], path: str) -> None:
        """Export a composed task to the target format.

        Args:
            task: Composed task dict with at least a 'primitives' key.
            path: Output file path.
        """
        ...

    def export_batch(self, tasks: list[dict[str, Any]], path: str) -> None:
        """Export multiple tasks to a single file.

        Default implementation raises NotImplementedError.
        Subclasses may override for formats that support batching.

        Args:
            tasks: List of composed task dicts.
            path: Output file path.
        """
        raise NotImplementedError("Batch export not supported by this exporter.")
