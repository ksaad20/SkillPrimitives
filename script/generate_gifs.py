#!/usr/bin/env python3
"""
generate_gifs.py — Auto-render preview GIFs for every zoo primitive.

Captures animated previews of each primitive by rendering its HTML
in a headless browser and recording the result as an optimized GIF.

Usage:
    ./scripts/generate_gifs.py --all              # Generate all previews
    ./scripts/generate_gifs.py --primitive button # Generate only for 'button'
    ./scripts/generate_gifs.py --dry-run          # Show what would be generated
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

from PIL import Image
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

console = Console()

# ── Configuration ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ZOO_DIR = PROJECT_ROOT / "zoo"
OUTPUT_DIR = PROJECT_ROOT / "assets" / "previews"
MANIFEST_FILE = PROJECT_ROOT / "zoo_manifest.json"

DEFAULT_FPS = 30
DEFAULT_DURATION = 3  # seconds
DEFAULT_RESOLUTION = (800, 600)


class GIFGenerator:
    def __init__(
        self,
        zoo_dir: Path,
        output_dir: Path,
        fps: int = DEFAULT_FPS,
        duration: int = DEFAULT_DURATION,
        resolution: tuple[int, int] = DEFAULT_RESOLUTION,
    ):
        self.zoo_dir = zoo_dir
        self.output_dir = output_dir
        self.fps = fps
        self.duration = duration
        self.resolution = resolution
        self.frame_count = fps * duration
        self.stats = {"generated": 0, "skipped": 0, "failed": 0, "optimized": 0}

    # ── Discovery ──────────────────────────────────────────────────────────────
    def load_manifest(self) -> list[dict]:
        """Load the zoo manifest for primitive metadata."""
        if not MANIFEST_FILE.exists():
            console.print(
                f"[red]Manifest not found: {MANIFEST_FILE}\n"
                f"Run ./scripts/build_zoo.py first.[/red]"
            )
            sys.exit(1)

        with open(MANIFEST_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("primitives", [])

    def discover_targets(self, primitive_name: Optional[str] = None) -> list[dict]:
        """Determine which primitives need GIF generation."""
        primitives = self.load_manifest()

        if primitive_name:
            primitives = [p for p in primitives if p["name"] == primitive_name]
            if not primitives:
                console.print(f"[red]Primitive '{primitive_name}' not found in manifest.[/red]")
                sys.exit(1)

        return primitives

    # ── Rendering ──────────────────────────────────────────────────────────────
    def needs_generation(self, primitive: dict) -> bool:
        """Check if GIF needs regeneration (missing or outdated)."""
        gif_path = self.output_dir / f"{primitive['name']}.gif"
        meta_path = self.zoo_dir / primitive["name"] / "meta.json"

        if not gif_path.exists():
            return True

        # Check if primitive was rebuilt after GIF was generated
        gif_mtime = gif_path.stat().st_mtime
        if meta_path.exists():
            meta_mtime = meta_path.stat().st_mtime
            return meta_mtime > gif_mtime

        return False

    def render_frames_playwright(self, html_path: Path, output_frames_dir: Path) -> list[Path]:
        """Render frames using Playwright (recommended)."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            console.print(
                "[red]Playwright not installed. Run: pip install playwright && playwright install[/red]"
            )
            sys.exit(1)

        frame_paths = []
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(
                viewport={
                    "width": self.resolution[0],
                    "height": self.resolution[1],
                }
            )
            page.goto(f"file://{html_path.resolve()}")

            # Wait for any animations to settle
            page.wait_for_timeout(500)

            interval = 1000 / self.fps  # ms between frames
            for i in range(self.frame_count):
                frame_path = output_frames_dir / f"frame_{i:04d}.png"
                page.screenshot(path=str(frame_path), full_page=False)
                frame_paths.append(frame_path)
                page.wait_for_timeout(int(interval))

            browser.close()

        return frame_paths

    def render_frames_fallback(self, html_path: Path, output_frames_dir: Path) -> list[Path]:
        """Fallback frame rendering using selenium if playwright unavailable."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
        except ImportError:
            console.print("[red]Neither Playwright nor Selenium available.[/red]")
            sys.exit(1)

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument(f"--window-size={self.resolution[0]},{self.resolution[1]}")

        driver = webdriver.Chrome(options=chrome_options)
        driver.get(f"file://{html_path.resolve()}")
        time.sleep(0.5)

        frame_paths = []
        interval = 1.0 / self.fps
        for i in range(self.frame_count):
            frame_path = output_frames_dir / f"frame_{i:04d}.png"
            driver.save_screenshot(str(frame_path))
            frame_paths.append(frame_path)
            time.sleep(interval)

        driver.quit()
        return frame_paths

    def compile_gif(self, frame_paths: list[Path], output_path: Path) -> None:
        """Compile PNG frames into an optimized GIF."""
        images = [Image.open(f) for f in frame_paths]

        # Convert to palette mode for smaller file size
        images = [img.convert("P", palette=Image.ADAPTIVE, colors=128) for img in images]

        duration_ms = int(1000 / self.fps)
        images[0].save(
            output_path,
            save_all=True,
            append_images=images[1:],
            duration=duration_ms,
            loop=0,
            optimize=True,
        )

        # Further optimize with gifsicle if available
        if shutil.which("gifsicle"):
            subprocess.run(
                [
                    "gifsicle",
                    "--optimize=3",
                    "--colors",
                    "128",
                    "-o",
                    str(output_path),
                    str(output_path),
                ],
                check=False,
                capture_output=True,
            )
            self.stats["optimized"] += 1

    # ── Orchestration ──────────────────────────────────────────────────────────
    def generate(
        self, primitive_name: Optional[str] = None, dry_run: bool = False, force: bool = False
    ):
        """Generate GIFs for all or selected primitives."""
        console.rule("[bold magenta]🎬 GIF Generator[/bold magenta]")

        targets = self.discover_targets(primitive_name)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Filter to only those needing generation
        if not force:
            targets = [t for t in targets if self.needs_generation(t)]

        if not targets:
            console.print("[green]All GIFs are up to date. Nothing to do.[/green]")
            return

        if dry_run:
            console.print(f"[cyan]Would generate {len(targets)} GIF(s):[/cyan]")
            for t in targets:
                console.print(f"  • {t['name']} → {self.output_dir / (t['name'] + '.gif')}")
            return

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Rendering GIFs...", total=len(targets))

            for primitive in targets:
                name = primitive["name"]
                progress.update(task, description=f"[cyan]{name}[/cyan]")

                html_path = self.zoo_dir / name / "index.html"
                if not html_path.exists():
                    html_path = self.zoo_dir / name / f"{name}.html"

                if not html_path.exists():
                    console.print(f"[yellow]  No HTML entry point for {name}, skipping.[/yellow]")
                    self.stats["skipped"] += 1
                    progress.advance(task)
                    continue

                with tempfile.TemporaryDirectory() as tmpdir:
                    frames_dir = Path(tmpdir) / "frames"
                    frames_dir.mkdir()

                    try:
                        # Prefer playwright, fallback to selenium
                        try:
                            frame_paths = self.render_frames_playwright(html_path, frames_dir)
                        except Exception:
                            frame_paths = self.render_frames_fallback(html_path, frames_dir)

                        output_path = self.output_dir / f"{name}.gif"
                        self.compile_gif(frame_paths, output_path)
                        self.stats["generated"] += 1

                        size_kb = output_path.stat().st_size / 1024
                        console.print(f"  [green]✓[/green] {name}.gif ({size_kb:.1f} KB)")

                    except Exception as e:
                        console.print(f"  [red]✗[/red] {name}: {e}")
                        self.stats["failed"] += 1

                progress.advance(task)

        self._report()

    def _report(self):
        table = Table(title="GIF Generation Summary", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right", style="green")

        table.add_row("Generated", str(self.stats["generated"]))
        table.add_row("Optimized (gifsicle)", str(self.stats["optimized"]))
        table.add_row("Skipped", str(self.stats["skipped"]))
        table.add_row("Failed", str(self.stats["failed"]))

        console.print(table)


def main():
    parser = argparse.ArgumentParser(description="Generate preview GIFs for zoo primitives")
    parser.add_argument("--all", action="store_true", help="Generate all GIFs")
    parser.add_argument("--primitive", help="Generate only for this primitive")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be generated")
    parser.add_argument(
        "--force", action="store_true", help="Force regeneration even if up to date"
    )
    parser.add_argument(
        "--fps", type=int, default=DEFAULT_FPS, help=f"Frames per second (default: {DEFAULT_FPS})"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=DEFAULT_DURATION,
        help=f"Duration in seconds (default: {DEFAULT_DURATION})",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=DEFAULT_RESOLUTION[0],
        help=f"Viewport width (default: {DEFAULT_RESOLUTION[0]})",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=DEFAULT_RESOLUTION[1],
        help=f"Viewport height (default: {DEFAULT_RESOLUTION[1]})",
    )
    args = parser.parse_args()

    if not args.all and not args.primitive:
        parser.error("Specify --all or --primitive <name>")

    generator = GIFGenerator(
        ZOO_DIR,
        OUTPUT_DIR,
        fps=args.fps,
        duration=args.duration,
        resolution=(args.width, args.height),
    )

    generator.generate(
        primitive_name=args.primitive,
        dry_run=args.dry_run,
        force=args.force,
    )


if __name__ == "__main__":
    main()
