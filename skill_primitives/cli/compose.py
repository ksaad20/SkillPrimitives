"""CLI: Compose primitives into task sequences.

Usage:
    python -m skill_primitives.compose --library ./my_skills/ --instructions "reach" "grasp" "lift" "place"
    python -m skill_primitives.compose --library ./my_skills/ --instructions-file task.txt --output task.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from skill_primitives.core.composer import SkillLibrary, compose
from skill_primitives.io.exporters import get_exporter  # type: ignore[attr-defined]


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(
        description="Compose skill primitives into tasks from natural language",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  %(prog)s --library ./my_skills/ --instructions "reach the red cube" "grasp firmly" "lift 5cm" "place in bin"\n'
            "  %(prog)s --library ./my_skills/ --instructions-file task.txt --output task.json --format json\n"
            '  %(prog)s --library ./my_skills/ --instructions "reach" "grasp" "lift" --output task.parquet --format lerobot'
        ),
    )
    parser.add_argument(
        "--library",
        required=True,
        help="Path to skill library directory",
    )
    parser.add_argument(
        "--instructions",
        nargs="+",
        help="Natural language instructions (one per primitive)",
    )
    parser.add_argument(
        "--instructions-file",
        help="File containing one instruction per line",
    )
    parser.add_argument(
        "--output",
        default="composed_task.json",
        help="Output file path (default: composed_task.json)",
    )
    parser.add_argument(
        "--format",
        default="json",
        choices=["json", "parquet", "lerobot"],
        help="Output format (default: json)",
    )
    args = parser.parse_args(argv)

    # Load instructions
    if args.instructions_file:
        path = Path(args.instructions_file)
        if not path.exists():
            print(f"Error: Instructions file not found: {path}")
            return 1
        instructions = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    elif args.instructions:
        instructions = args.instructions
    else:
        print("Error: Provide --instructions or --instructions-file")
        return 1

    print(f"Loading skill library from: {args.library}")
    lib = SkillLibrary.from_disk(args.library)

    print(f"Composing task from {len(instructions)} instructions:")
    for i, inst in enumerate(instructions, 1):
        print(f"  {i}. {inst}")

    task = compose(instructions, library=lib)

    print("")
    print(f"Composed {len(task.skills)} skills:")
    for i, skill in enumerate(task.skills, 1):
        print(f"  {i}. [{skill.skill_type}] {skill.description}")

    # Export
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    exporter = get_exporter(args.format)

    # Prepare task dict for exporter
    task_dict = {
        "primitives": task.primitives,
        "num_primitives": len(task.skills),
        "estimated_duration": task.duration,
    }

    exporter.export(task_dict, str(output_path))

    print("")
    print("{}".format("=" * 50))
    print(f"Task exported to: {output_path.absolute()}")
    print(f"Format: {args.format}")
    print("{}".format("=" * 50))

    return 0


if __name__ == "__main__":
    sys.exit(main())
