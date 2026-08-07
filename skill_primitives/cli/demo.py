"""CLI: Run the 10-second hello demo.

Usage:
    python -m skill_primitives.demo
"""

from __future__ import annotations

import sys

from skill_primitives.core.segmenter import segment_episode
from skill_primitives.core.composer import compose
from skill_primitives.core.annotator import Annotator


def main(argv=None):
    print("=" * 60)
    print("  Skill Primitives — Hello Demo")
    print("  Natural Language to Robot Motion")
    print("=" * 60)

    # Step 1: Segment
    print("
[1/4] Segmenting a sample LeRobot episode...")
    print("      Dataset: lerobot/pusht")
    print("      Episode: 0")

    try:
        primitives = segment_episode("lerobot/pusht", episode=0)
        source = "live"
    except Exception as e:
        print(f"      Note: Using synthetic fallback ({e})")
        primitives = [
            {"type": "reach", "start": 0, "end": 15, "confidence": 0.92},
            {"type": "grasp", "start": 15, "end": 25, "confidence": 0.88},
            {"type": "lift", "start": 25, "end": 40, "confidence": 0.95},
            {"type": "place", "start": 40, "end": 55, "confidence": 0.90},
        ]
        source = "synthetic"

    print(f"
      Detected {len(primitives)} primitives ({source}):")
    for p in primitives:
        print(f"        {p['type']:10s} | frames {p['start']:3d}-{p['end']:3d} | conf={p['confidence']:.2f}")

    # Step 2: Annotate
    print("
[2/4] Annotating with natural language...")
    annotator = Annotator()
    annotated = annotator.annotate_batch(primitives)

    print("      Descriptions:")
    for p in annotated:
        print(f"        [{p['type']:10s}] {p['description']}")

    # Step 3: Compose novel task
    print("
[3/4] Composing a novel task (never in training data)...")
    novel_instructions = [
        "reach the screwdriver",
        "grasp the handle firmly",
        "lift vertically 3cm",
        "transport to the panel",
        "orient tip downward",
        "place gently into slot",
    ]

    print("      Instructions:")
    for i, inst in enumerate(novel_instructions, 1):
        print(f"        {i}. {inst}")

    task = compose(novel_instructions)

    print(f"
      Composed {len(task.primitives)} primitives:")
    for i, p in enumerate(task.primitives, 1):
        print(f"        {i}. [{p['type']:12s}] {p['instruction']}")

    # Step 4: Export
    print("
[4/4] Exporting composed task...")
    import tempfile
    import json

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    task.export_json(tmp.name)
    tmp.close()

    # Show the exported content
    with open(tmp.name) as f:
        exported = json.load(f)

    print(f"      Exported to: {tmp.name}")
    print(f"      Task duration: {exported['task']['estimated_duration']:.1f}s")
    print(f"      Num primitives: {exported['task']['num_primitives']}")

    print("
" + "=" * 60)
    print("  Demo complete!")
    print("  Try it yourself:")
    print("    python -m skill_primitives.segment --dataset lerobot/pusht --output ./skills/")
    print("    python -m skill_primitives.compose --library ./skills/ --instructions "reach" "grasp" "lift"")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
