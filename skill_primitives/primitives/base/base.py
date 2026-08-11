"""base.py — Abstract base class for annotation primitives.

Every primitive in the annotation engine (grasp, reach, retract, etc.)
must subclass :class:`Primitive` and implement :meth:`detect`. The
``annotate`` script drives the full pipeline:
``detect → validate → describe``.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, ClassVar

import numpy as np

logger = logging.getLogger(__name__)


class Primitive(ABC):
    """Base class for robotics skill annotation primitives.

    Subclasses define how to detect their signature in raw demonstration
    trajectories, validate the quality of detected segments, and generate
    natural-language descriptions for training the NL→motion transformer.
    """

    # ── Class-level metadata ───────────────────────────────────────────────
    name: ClassVar[str] = ""
    version: ClassVar[str] = "0.0.0"
    category: ClassVar[str] = "utility"
    description: ClassVar[str] = ""
    author: ClassVar[str] = ""

    # ── Core annotation interface ──────────────────────────────────────────
    @abstractmethod
    def detect(
        self,
        gripper: np.ndarray,
        state: np.ndarray | None = None,
        velocity: np.ndarray | None = None,
    ) -> list[dict[str, Any]]:
        """Find segments in demonstration data that match this primitive.

        Args:
            gripper: 1-D array of normalized gripper openings [0, 1].
            state: 2-D array of robot states (joints or pose) per timestep.
            velocity: 2-D array of velocities per timestep.

        Returns:
            List of segment dicts. Each dict must contain at least
            ``{"type": self.name, "start": int, "end": int}``.
        """
        ...  # pragma: no cover

    def validate(self, segment: dict[str, Any]) -> bool:
        """Check whether a detected segment is valid.

        The default implementation verifies that ``segment["type"]``
        matches :attr:`name`. Subclasses may add domain-specific checks
        (e.g., duration thresholds, signal quality).
        """
        return segment.get("type") == self.name

    def describe(self, segment: dict[str, Any]) -> str:
        """Generate a natural-language description of *segment*.

        Override to produce task-specific phrasing used by the transformer.
        """
        return f"perform {self.name}"

    # ── Pipeline convenience ───────────────────────────────────────────────
    def annotate(
        self,
        gripper: np.ndarray,
        state: np.ndarray | None = None,
        velocity: np.ndarray | None = None,
    ) -> list[dict[str, Any]]:
        """Run the full annotation pipeline in one call.

        This is the entry point used by the ``annotate`` script.
        """
        segments = self.detect(gripper, state, velocity)
        results: list[dict[str, Any]] = []
        for seg in segments:
            if self.validate(seg):
                seg["description"] = self.describe(seg)
                results.append(seg)
        return results

    # ── Introspection helpers ──────────────────────────────────────────────
    @classmethod
    def get_metadata(cls) -> dict[str, Any]:
        """Return static metadata consumed by ``build_zoo.py``."""
        return {
            "name": cls.name,
            "version": cls.version,
            "category": cls.category,
            "description": cls.description,
            "author": cls.author,
        }

    def __repr__(self) -> str:
        return f"<Primitive {self.name}@{self.version} ({self.category})>"
