"""CLI entry points for Skill Primitives.

Command-line interfaces for the full pipeline:
- segment: Extract primitives from LeRobot datasets
- annotate: Label primitives with natural language descriptions
- compose: Chain primitives into executable task sequences
- demo: Run the interactive hello-world demonstration

These can be invoked via:
    python -m skill_primitives.segment [args]
    python -m skill_primitives.annotate [args]
    python -m skill_primitives.compose [args]
    python -m skill_primitives.demo

Or imported programmatically:
    from skill_primitives.cli.segment import main as segment_main
    from skill_primitives.cli.compose import main as compose_main
"""

from skill_primitives.cli.segment import main as segment
from skill_primitives.cli.annotate import main as annotate
from skill_primitives.cli.compose import main as compose
from skill_primitives.cli.demo import main as demo

__all__ = [
    "segment",
    "annotate",
    "compose",
    "demo",
]
