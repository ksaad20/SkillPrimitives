#!/usr/bin/env python3
"""build_zoo.py — Regenerate all zoo/ artifacts from primitive sources.

Scans the primitives/ directory, validates each skill definition,
renders templates, and writes compiled artifacts to zoo/.

Usage:
    ./scripts/build_zoo.py              # Full rebuild
    ./scripts/build_zoo.py --watch      # Watch mode for development
    ./scripts/build_zoo.py --primitives button card modal  # Selective build
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()

# ── Configuration ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRIMITIVES_DIR = PROJECT_ROOT / "skill_primitives" / "primitives"
ZOO_DIR = PROJECT_ROOT / "zoo"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
META_FILE = PROJECT_ROOT / "zoo_manifest.json"

REQUIRED_FIELDS = {"name", "version", "category", "description", "author", "files"}
VALID_CATEGORIES = {
    "ui",
    "animation",
    "layout",
    "interaction",
    "accessibility",
    "utility",
}


class ZooBuilder:
    def __init__(self, primitives_dir: Path, zoo_dir: Path, templates_dir: Path):
        self.primitives_dir = primitives_dir
        self.zoo_dir = zoo_dir
        self.templates_dir = templates_dir
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self.manifest: dict = {"generated_at": None, "primitives": []}
        self.errors: list[str] = []
        self.warnings: list[str] = []

    # ── Discovery ──────────────────────────────────────────────────────────────
    def discover_primitives(self, names: set[str] | None = None) -> list[Path]:
        """Find all primitive directories."""
        if not self.primitives_dir.exists():
            console.print(f"[red]Primitives directory not found:{self.primitives_dir}[/red]")
            sys.exit(1)

        candidates = [
            d
            for d in self.primitives_dir.iterdir()
            if d.is_dir() and not d.name.startswith((".", "_"))
        ]

        if names:
            candidates = [c for c in candidates if c.name in names]

        return sorted(candidates)

    # ── Validation ─────────────────────────────────────────────────────────────
    def validate_primitive(self, primitive_dir: Path) -> dict | None:
        """Validate a primitive directory structure and metadata."""
        name = primitive_dir.name
        spec_path = primitive_dir / "spec.yaml"

        if not spec_path.exists():
            self.errors.append(f"{name}: Missing spec.yaml")
            return None

        try:
            with open(spec_path, encoding="utf-8") as f:
                spec = yaml.safe_load(f)
        except yaml.YAMLError as e:
            self.errors.append(f"{name}: Invalid YAML in spec.yaml — {e}")
            return None

        missing = REQUIRED_FIELDS - set(spec.keys())
        if missing:
            self.errors.append(f"{name}: Missing required fields: {missing}")
            return None

        if spec["category"] not in VALID_CATEGORIES:
            self.warnings.append(f"{name}: Unknown category '{spec['category']}'")

        # Check referenced files exist (handles both string and dict entries)
        for file_entry in spec.get("files", []):
            if isinstance(file_entry, str):
                src = primitive_dir / file_entry
                if not src.exists():
                    self.errors.append(f"{name}: Referenced file missing:{file_entry}")
                    return None
            elif isinstance(file_entry, dict):
                src = primitive_dir / file_entry["src"]
                if not src.exists():
                    self.errors.append(f"{name}: Referenced file missing:{file_entry['src']}")
                    return None
            else:
                self.errors.append(f"{name}: Invalid file entry type:{type(file_entry)}")
                return None

        return spec

    # ── Build ──────────────────────────────────────────────────────────────────
    def build_primitive(self, primitive_dir: Path, spec: dict) -> dict:
        """Build a single primitive into the zoo."""
        name = primitive_dir.name
        output_dir = self.zoo_dir / name
        output_dir.mkdir(parents=True, exist_ok=True)

        # Copy source files (handles both string and dict entries)
        for file_entry in spec.get("files", []):
            if isinstance(file_entry, str):
                src = primitive_dir / file_entry
                dst_name = file_entry
            else:
                src = primitive_dir / file_entry["src"]
                dst_name = file_entry.get("dest", file_entry["src"])
            dst = output_dir / dst_name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

        # Render template if provided
        if "template" in spec:
            template_name = spec["template"]
            template = self.env.get_template(template_name)
            rendered = template.render(
                primitive=spec,
                name=name,
                files=spec.get("files", []),
            )
            out_file = output_dir / spec.get("template_output", "index.html")
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(rendered)

        # Generate metadata artifact
        meta = {
            "name": name,
            "version": spec["version"],
            "category": spec["category"],
            "description": spec["description"],
            "author": spec["author"],
            "files": [
                f if isinstance(f, str) else f.get("dest", f["src"]) for f in spec.get("files", [])
            ],
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        with open(output_dir / "metadata.yaml", "w", encoding="utf-8") as f:
            yaml.dump(meta, f, default_flow_style=False, sort_keys=False)

        return meta

    # ── Orchestration ──────────────────────────────────────────────────────────
    def build(self, names: set[str] | None = None) -> bool:
        """Run the full build process."""
        console.rule("[bold blue] Zoo Builder [/bold blue]")

        primitives = self.discover_primitives(names)
        if not primitives:
            console.print("[yellow]No primitives found to build.[/yellow]")
            return True

        self.zoo_dir.mkdir(parents=True, exist_ok=True)

        # Skip Unicode spinner in CI to avoid Windows console crashes
        is_ci = os.environ.get("CI") == "true"
        progress_columns = [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
        ]
        if is_ci:
            progress_columns = [TextColumn("[progress.description]{task.description}")]

        with Progress(
            *progress_columns,
            console=console,
        ) as progress:
            task = progress.add_task("Building primitives...", total=len(primitives))

            for primitive_dir in primitives:
                progress.update(
                    task,
                    description=f"[cyan]Building {primitive_dir.name}...[/cyan]",
                )

                spec = self.validate_primitive(primitive_dir)
                if spec is None:
                    progress.advance(task)
                    continue

                meta = self.build_primitive(primitive_dir, spec)
                self.manifest["primitives"].append(meta)
                progress.advance(task)

        # Write manifest
        self.manifest["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(META_FILE, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, indent=2)

        # Report
        self._report()
        return len(self.errors) == 0

    def _report(self):
        table = Table(title="Build Summary", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right", style="green")

        total = len(self.manifest["primitives"])
        table.add_row("Primitives Built", str(total))
        table.add_row("Errors", str(len(self.errors)))
        table.add_row("Warnings", str(len(self.warnings)))

        console.print(table)

        if self.errors:
            console.print("[bold red]Errors:[/bold red]")
            for err in self.errors:
                console.print(f"  • {err}")

        if self.warnings:
            console.print("[bold yellow]Warnings:[/bold yellow]")
            for warn in self.warnings:
                console.print(f"  • {warn}")

    def watch(self):
        """Watch primitives/ for changes and rebuild."""
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError:
            console.print("[red]watchdog required for --watch. " "Run: pip install watchdog[/red]")
            sys.exit(1)

        class RebuildHandler(FileSystemEventHandler):
            def __init__(self, builder: ZooBuilder):
                self.builder = builder
                self.debounce = 0

            def on_any_event(self, event):
                if event.is_directory or event.src_path.endswith(("~", ".swp")):
                    return
                now = time.time()
                if now - self.debounce > 1.0:
                    self.debounce = now
                    console.print(f"[yellow]Change detected: {event.src_path}[/yellow]")
                    self.builder.build()
                    console.rule()

        console.rule("[bold blue]Watch Mode[/bold blue]")
        console.print("Monitoring primitives/ for changes... (Ctrl+C to stop)")

        self.build()
        handler = RebuildHandler(self)
        observer = Observer()
        observer.schedule(handler, str(self.primitives_dir), recursive=True)
        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            console.print("[green]Watch mode stopped.[/green]")
        observer.join()


def main():
    parser = argparse.ArgumentParser(description="Build the skills primitive zoo")
    parser.add_argument("--watch", action="store_true", help="Watch mode")
    parser.add_argument("--primitives", nargs="+", help="Build only specified primitives")
    args = parser.parse_args()

    builder = ZooBuilder(PRIMITIVES_DIR, ZOO_DIR, TEMPLATES_DIR)
    names = set(args.primitives) if args.primitives else None

    if args.watch:
        builder.watch()
    else:
        success = builder.build(names)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
