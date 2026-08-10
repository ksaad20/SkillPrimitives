"""CLI demo command for skill primitives."""

from __future__ import annotations

import json
import tempfile

from skill_primitives.core.annotator import Annotator
from skill_primitives.core.composer import compose
from skill_primitives.core.segmenter import Segmenter
from skill_primitives.io.lerobot_adapter import LeRobotAdapter


def main() -> None:
    print("=" * 60)
    print("  Skill Primitives — Hello Demo")
    print("  Natural Language to Robot Motion")
    print("=" * 60)

    # Step 1: Segment
    print("")
    print("[1/4] Segmenting a sample LeRobot episode...")
    print("      Dataset: lerobot/pusht")
    print("      Episode: 0")

    try:
        adapter = LeRobotAdapter()
        segmenter = Segmenter()
        episode = adapter.load_episode("lerobot/pusht", episode_index=0, revision="main")
        primitives = segmenter.segment(episode)
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

    print("")
    print(f"      Detected {len(primitives)} primitives ({source})")
    for p in primitives:
        line = "{:10s} | frames {:3d}-{:3d} | conf={:.2f}".format(
            p["type"], p["start"], p["end"], p["confidence"]
        )
        print(line)

    # Step 2: Annotate
    print("")
    print("[2/4] Annotating with natural language...")
    annotator = Annotator()
    annotated = annotator.annotate_batch(primitives)

    print("      Descriptions:")
    for p in annotated:
        print("        [{:10s}] {}".format(p["type"], p["description"]))

    # Step 3: Compose novel task
    print("")
    print("[3/4] Composing a novel task (never in training data)...")
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

    print("")
    print(f"      Composed {len(task.primitives)} primitives:")
    for i, p in enumerate(task.primitives, 1):
        print("        {}. [{:12s}] {}".format(i, p["type"], p["instruction"]))

    # Step 4: Export
    print("")
    print("[4/4] Exporting composed task...")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        task.export_json(tmp.name)

    # Show the exported content
    with open(tmp.name) as f:
        exported = json.load(f)

    print(f"      Exported to: {tmp.name}")
    print("      Task duration: {:.1f}s".format(exported["task"]["estimated_duration"]))
    print("      Num primitives: {}".format(exported["task"]["num_primitives"]))

    print("")
    print("=" * 60)
    print("  Demo complete!")
    print("  Try it yourself:")
    print("    python -m skill_primitives.segment --dataset lerobot/pusht" " --output ./skills/")
    print(
        "    python -m skill_primitives.compose --library ./skills/"
        ' --instructions "reach" "grasp" "lift"'
    )
    print("=" * 60)


if __name__ == "__main__":
    main()
