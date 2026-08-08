from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from skill_primitives.core.annotator import Annotator


def main(argv: Any = None) -> None:
    parser = argparse.ArgumentParser(
        description="Annotate skill primitives with natural language descriptions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input ./my_skills/ --provider ollama
  %(prog)s --input ./my_skills/ --provider groq --model llama-3.1-8b-instant
  %(prog)s --input ./my_skills/ --provider openai --model gpt-4o-mini
        """.strip(),
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Directory containing segmented primitives",
    )
    parser.add_argument(
        "--provider",
        default="ollama",
        choices=["ollama", "groq", "openai"],
        help="LLM provider (default: ollama)",
    )
    parser.add_argument(
        "--model",
        default="llama3.1",
        help="Model name for the provider",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be annotated without writing files",
    )
    args = parser.parse_args(argv)

    input_dir = Path(args.input)
    if not input_dir.exists():
        print(f"Error: Input directory not found: {input_dir}")
        return

    annotator = Annotator(provider=args.provider, model=args.model)

    # Find all metadata files
    meta_files = sorted(input_dir.rglob("*.json"))
    if not meta_files:
        print(f"No .json metadata files found in {input_dir}")
        return

    print(f"Found {len(meta_files)} primitive metadata files")
    print(f"Using provider: {args.provider} / {args.model}")
    print()

    annotated_count = 0

    for meta_file in meta_files:
        try:
            with open(meta_file) as f:
                primitive = json.load(f)
        except json.JSONDecodeError as e:
            print(f"  Skipping {meta_file}: invalid JSON ({e})")
            continue

        # Skip already annotated
        if "description" in primitive and primitive["description"]:
            print(f"  Skipping {meta_file.name}: already annotated")
            continue

        description = annotator.annotate(primitive)

        if args.dry_run:
            print(f"  [DRY-RUN] {meta_file.name}: {description}")
        else:
            primitive["description"] = description
            with open(meta_file, "w") as f:
                json.dump(primitive, f, indent=2)
            print(f"  Annotated {meta_file.name}: {description}")

        annotated_count += 1

    print()
    print(f"{'='*50}")
    if args.dry_run:
        print(f"Dry run complete. Would annotate {annotated_count} files.")
    else:
        print(f"Annotation complete! Updated {annotated_count} files.")
    print(f"{'='*50}")

    return


if __name__ == "__main__":
    main()
