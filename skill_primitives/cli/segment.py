"""CLI: Segment LeRobot datasets into primitives.

Usage:
    python -m skill_primitives.segment --dataset lerobot/pusht --output ./skills/
    python -m skill_primitives.segment --dataset lerobot/pusht --episodes 0 1 2 --output ./skills/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from skill_primitives.core.annotator import Annotator
from skill_primitives.core.segmenter import segment_episode
from skill_primitives.io.lerobot_adapter import LeRobotAdapter


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Segment LeRobot episodes into skill primitives",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s --dataset lerobot/pusht --output ./my_skills/\n"
            "  %(prog)s --dataset lerobot/pusht --episodes 0 1 2 --output ./my_skills/\n"
            "  %(prog)s --dataset lerobot/pusht --annotate --provider ollama --output ./my_skills/"
        ),
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="HuggingFace dataset ID (e.g., lerobot/pusht)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output directory for segmented skills",
    )
    parser.add_argument(
        "--episodes",
        type=int,
        nargs="+",
        default=None,
        help="Episode indices to segment (default: all)",
    )
    parser.add_argument(
        "--annotate",
        action="store_true",
        help="Annotate segments with natural language descriptions",
    )
    parser.add_argument(
        "--provider",
        default="ollama",
        choices=["ollama", "groq", "openai"],
        help="LLM provider for annotation (default: ollama)",
    )
    parser.add_argument(
        "--model",
        default="llama3.1",
        help="Model name for the provider",
    )
    parser.add_argument(
        "--format",
        default="json",
        choices=["json", "yaml"],
        help="Metadata output format (default: json)",
    )
    args = parser.parse_args(argv)

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Determine episodes to process
    if args.episodes:
        episodes = args.episodes
    else:
        try:
            adapter = LeRobotAdapter()
            episodes = adapter.list_episodes(args.dataset)
            print("Found {} episodes in {}".format(len(episodes), args.dataset))
        except Exception as e:
            print("Could not list episodes: {}".format(e))
            print("Falling back to episode 0 only")
            episodes = [0]

    annotator = None
    if args.annotate:
        annotator = Annotator(provider=args.provider, model=args.model)

    total_segments = 0

    for ep_idx in episodes:
        print("")
        print("Processing episode {}...".format(ep_idx))

        try:
            primitives = segment_episode(args.dataset, episode=ep_idx)
        except Exception as e:
            print("  Failed to segment episode {}: {}".format(ep_idx, e))
            continue

        print("  Found {} primitives".format(len(primitives)))

        # Annotate if requested
        if annotator:
            primitives = annotator.annotate_batch(primitives)

        # Write segments to disk
        for i, primitive in enumerate(primitives):
            ptype = primitive["type"]
            pdir = out_dir / ptype
            pdir.mkdir(exist_ok=True)

            # Write metadata
            meta_path = pdir / "episode_{:03d}_seg_{:03d}.json".format(ep_idx, i)
            with open(meta_path, "w") as f:
                json.dump(primitive, f, indent=2)

            total_segments += 1

    print("")
    print("{}".format("=" * 50))
    print("Segmentation complete!")
    print("  Dataset: {}".format(args.dataset))
    print("  Episodes: {}".format(len(episodes)))
    print("  Total segments: {}".format(total_segments))
    print("  Output: {}".format(out_dir.absolute()))
    print("{}".format("=" * 50))

    return 0


if __name__ == "__main__":
    sys.exit(main())
