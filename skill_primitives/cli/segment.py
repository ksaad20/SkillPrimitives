"""CLI command to segment LeRobot episodes into skill primitives."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from skill_primitives.core.segmenter import Segmenter
from skill_primitives.io.lerobot_adapter import LeRobotAdapter


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Segment LeRobot episodes into skill primitives")
    parser.add_argument("dataset", help="HuggingFace dataset ID (e.g., lerobot/pusht)")
    parser.add_argument(
        "--output-dir", "-o", type=Path, default=Path("segments"), help="Output directory"
    )
    parser.add_argument("--episode", "-e", type=int, default=0, help="Episode index to segment")
    parser.add_argument(
        "--revision",
        "-r",
        type=str,
        required=True,
        help="Git revision (commit hash or tag) to pin the dataset version",
    )
    parser.add_argument("--visualize", "-v", action="store_true", help="Generate visualization")
    args = parser.parse_args(argv)

    adapter = LeRobotAdapter()
    segmenter = Segmenter()

    episodes = adapter.list_episodes(args.dataset, revision=args.revision)
    print(f"Dataset has {len(episodes)} episode(s): {episodes}")

    if args.episode not in episodes:
        print(f"Error: episode {args.episode} not found.", file=sys.stderr)
        return 1

    episode = adapter.load_episode(args.dataset, args.episode, revision=args.revision)
    print(f"Loaded episode {args.episode} with {episode['num_frames']} frames")

    segments = segmenter.segment(episode)
    print(f"Segmented into {len(segments)} skill primitive(s)")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for i, seg in enumerate(segments):
        out_path = args.output_dir / f"segment_{i:03d}.json"
        out_path.write_text(json.dumps(seg, indent=2))
        print(f"  Saved {out_path}")

    if args.visualize:
        viz_path = args.output_dir / "visualization.png"
        _visualize_segments(segments, viz_path)
        print(f"  Visualization saved to {viz_path}")

    return 0


def _visualize_segments(segments: list[dict[str, Any]], path: Path) -> None:
    """Create a simple visualization of detected segments."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Warning: matplotlib not installed, skipping visualization", file=sys.stderr)
        return

    if not segments:
        return

    fig, ax = plt.subplots(figsize=(10, 3))
    colors = {
        "reach": "blue",
        "grasp": "green",
        "lift": "orange",
        "transport": "purple",
        "place": "red",
    }

    for seg in segments:
        color = colors.get(seg["type"], "gray")
        ax.barh(seg["type"], seg["end"] - seg["start"], left=seg["start"], color=color, alpha=0.6)

    ax.set_xlabel("Frame")
    ax.set_title("Detected Skill Primitives")
    plt.tight_layout()
    plt.savefig(path)
    plt.close(fig)


if __name__ == "__main__":
    sys.exit(main())

return 0
