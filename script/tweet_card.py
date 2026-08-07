#!/usr/bin/env python3
"""
tweet_card.py — Auto-generate Twitter/X share card from benchmark results.

Renders a polished 1200×675 PNG card summarizing benchmark data,
ready to attach to tweets or use as social preview / og:image.

Usage:
    ./scripts/tweet_card.py --benchmark results.json --output card.png
    ./scripts/tweet_card.py --latest                    # Use latest benchmark
    ./scripts/tweet_card.py --theme dark                # Dark mode card
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont
from rich.console import Console

console = Console()

# ── Configuration ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BENCHMARKS_DIR = PROJECT_ROOT / "benchmarks"
ASSETS_DIR = PROJECT_ROOT / "assets"
FONTS_DIR = PROJECT_ROOT / "assets" / "fonts"

# Card dimensions (Twitter/X optimal)
CARD_WIDTH = 1200
CARD_HEIGHT = 675

# Theme palettes
THEMES = {
    "light": {
        "bg": "#FFFFFF",
        "bg_accent": "#F7F9FC",
        "text_primary": "#0F1419",
        "text_secondary": "#536471",
        "accent": "#1D9BF0",
        "accent_soft": "#E8F5FE",
        "border": "#EFF3F4",
        "success": "#00BA7C",
        "warning": "#FFAD1F",
        "danger": "#F4212E",
    },
    "dark": {
        "bg": "#0F1419",
        "bg_accent": "#16181C",
        "text_primary": "#E7E9EA",
        "text_secondary": "#71767B",
        "accent": "#1D9BF0",
        "accent_soft": "#1E2732",
        "border": "#2F3336",
        "success": "#00BA7C",
        "warning": "#FFAD1F",
        "danger": "#F4212E",
    },
    "brand": {
        "bg": "#0A0A0A",
        "bg_accent": "#141414",
        "text_primary": "#FFFFFF",
        "text_secondary": "#A0A0A0",
        "accent": "#FF6B35",
        "accent_soft": "#2A1A10",
        "border": "#2A2A2A",
        "success": "#4ADE80",
        "warning": "#FBBF24",
        "danger": "#F87171",
    },
}


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a font, falling back through preferred options."""
    candidates = []
    if bold:
        candidates = [
            FONTS_DIR / "Inter-Bold.ttf",
            FONTS_DIR / "Roboto-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    else:
        candidates = [
            FONTS_DIR / "Inter-Regular.ttf",
            FONTS_DIR / "Roboto-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]

    for path in candidates:
        if path and Path(path).exists():
            try:
                return ImageFont.truetype(str(path), size)
            except Exception:
                continue

    return ImageFont.load_default()


class TweetCard:
    def __init__(
        self,
        width: int = CARD_WIDTH,
        height: int = CARD_HEIGHT,
        theme: str = "dark",
    ):
        self.width = width
        self.height = height
        self.theme = THEMES.get(theme, THEMES["dark"])
        self.colors = self.theme

    # ── Drawing Helpers ────────────────────────────────────────────────────────
    def rounded_rect(
        self,
        draw: ImageDraw.Draw,
        xy: Tuple[int, int, int, int],
        radius: int,
        fill: Optional[str] = None,
        outline: Optional[str] = None,
        width: int = 1,
    ):
        """Draw a rounded rectangle."""
        draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)

    def draw_text_centered(
        self,
        draw: ImageDraw.Draw,
        text: str,
        font: ImageFont.FreeTypeFont,
        y: int,
        color: str,
    ) -> int:
        """Draw text horizontally centered, return right edge x."""
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (self.width - text_w) // 2
        draw.text((x, y), text, font=font, fill=color)
        return x + text_w

    def draw_metric_card(
        self,
        draw: ImageDraw.Draw,
        x: int,
        y: int,
        w: int,
        h: int,
        label: str,
        value: str,
        unit: str = "",
        trend: Optional[str] = None,
    ):
        """Draw a single metric card."""
        # Card background
        self.rounded_rect(draw, (x, y, x + w, y + h), radius=16, fill=self.colors["bg_accent"])

        # Label
        font_label = get_font(20)
        draw.text((x + 24, y + 20), label, font=font_label, fill=self.colors["text_secondary"])

        # Value
        font_value = get_font(48, bold=True)
        value_text = f"{value}{unit}"
        draw.text((x + 24, y + 52), value_text, font=font_value, fill=self.colors["text_primary"])

        # Trend indicator
        if trend:
            trend_color = self.colors["success"] if trend.startswith("+") else self.colors["danger"]
            font_trend = get_font(18, bold=True)
            draw.text((x + 24, y + 110), trend, font=font_trend, fill=trend_color)

    # ── Main Render ────────────────────────────────────────────────────────────
    def render(
        self,
        title: str,
        subtitle: str,
        metrics: List[Dict],
        footer: str,
        output_path: Path,
        logo_path: Optional[Path] = None,
    ):
        """Render the full card to a PNG file."""
        img = Image.new("RGB", (self.width, self.height), self.colors["bg"])
        draw = ImageDraw.Draw(img)

        # ── Header bar ─────────────────────────────────────────────────────────
        self.rounded_rect(
            draw,
            (40, 40, self.width - 40, 120),
            radius=20,
            fill=self.colors["accent_soft"],
        )

        # Logo / icon area
        if logo_path and logo_path.exists():
            try:
                logo = Image.open(logo_path).convert("RGBA")
                logo = logo.resize((48, 48), Image.LANCZOS)
                img.paste(logo, (72, 64), logo)
            except Exception:
                pass

        # Title
        font_title = get_font(36, bold=True)
        title_x = 140 if (logo_path and logo_path.exists()) else 72
        draw.text((title_x, 58), title, font=font_title, fill=self.colors["accent"])

        # Subtitle
        font_sub = get_font(20)
        draw.text((title_x, 100), subtitle, font=font_sub, fill=self.colors["text_secondary"])

        # ── Metrics grid ───────────────────────────────────────────────────────
        card_w = (self.width - 120) // len(metrics) - 20 if metrics else 200
        start_x = 60
        card_y = 160
        card_h = 360

        for i, metric in enumerate(metrics):
            x = start_x + i * (card_w + 24)
            self.draw_metric_card(
                draw,
                x,
                card_y,
                card_w,
                card_h,
                label=metric.get("label", ""),
                value=str(metric.get("value", "—")),
                unit=metric.get("unit", ""),
                trend=metric.get("trend"),
            )

        # ── Footer / watermark ─────────────────────────────────────────────────
        # Divider line
        draw.line(
            [(60, self.height - 80), (self.width - 60, self.height - 80)],
            fill=self.colors["border"],
            width=2,
        )

        font_footer = get_font(18)
        draw.text(
            (60, self.height - 60), footer, font=font_footer, fill=self.colors["text_secondary"]
        )

        # Date
        date_str = datetime.now().strftime("%Y-%m-%d")
        font_date = get_font(18)
        bbox = draw.textbbox((0, 0), date_str, font=font_date)
        date_w = bbox[2] - bbox[0]
        draw.text(
            (self.width - 60 - date_w, self.height - 60),
            date_str,
            font=font_date,
            fill=self.colors["text_secondary"],
        )

        # Save
        img.save(output_path, "PNG", optimize=True)
        console.print(f"[green]✓[/green] Card saved: {output_path}")


# ── Benchmark Parsing ────────────────────────────────────────────────────────
def load_benchmark(path: Path) -> Dict:
    """Load benchmark results from JSON."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_latest_benchmark() -> Path:
    """Find the most recent benchmark file in benchmarks/."""
    if not BENCHMARKS_DIR.exists():
        console.print(f"[red]Benchmarks directory not found: {BENCHMARKS_DIR}[/red]")
        sys.exit(1)

    files = sorted(BENCHMARKS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        console.print("[red]No benchmark JSON files found.[/red]")
        sys.exit(1)

    return files[0]


def extract_metrics(data: Dict) -> List[Dict]:
    """Extract displayable metrics from benchmark data."""
    metrics = []

    # Try common benchmark structures
    if "summary" in data:
        summary = data["summary"]
        if "total_primitives" in summary:
            metrics.append(
                {
                    "label": "Primitives",
                    "value": summary["total_primitives"],
                    "unit": "",
                }
            )
        if "avg_render_time_ms" in summary:
            metrics.append(
                {
                    "label": "Avg Render",
                    "value": f"{summary['avg_render_time_ms']:.1f}",
                    "unit": "ms",
                    "trend": summary.get("render_trend"),
                }
            )
        if "bundle_size_kb" in summary:
            metrics.append(
                {
                    "label": "Bundle Size",
                    "value": f"{summary['bundle_size_kb']:.1f}",
                    "unit": "KB",
                    "trend": summary.get("size_trend"),
                }
            )
        if "coverage_percent" in summary:
            metrics.append(
                {
                    "label": "Coverage",
                    "value": f"{summary['coverage_percent']:.0f}",
                    "unit": "%",
                    "trend": summary.get("coverage_trend"),
                }
            )

    # Fallback: just take top-level numeric keys
    if not metrics:
        for key, val in data.items():
            if isinstance(val, (int, float)) and not key.startswith("_"):
                metrics.append(
                    {
                        "label": key.replace("_", " ").title(),
                        "value": f"{val:.1f}" if isinstance(val, float) else str(val),
                        "unit": "",
                    }
                )
            if len(metrics) >= 4:
                break

    return metrics


# ── CLI ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Generate Twitter/X share card from benchmarks")
    parser.add_argument("--benchmark", type=Path, help="Path to benchmark JSON file")
    parser.add_argument("--latest", action="store_true", help="Use the most recent benchmark")
    parser.add_argument(
        "--output", type=Path, default=ASSETS_DIR / "tweet_card.png", help="Output PNG path"
    )
    parser.add_argument(
        "--theme", choices=list(THEMES.keys()), default="dark", help="Card color theme"
    )
    parser.add_argument("--title", default="Skills Primitive Zoo", help="Card title")
    parser.add_argument("--subtitle", help="Card subtitle (auto-generated if omitted)")
    parser.add_argument("--logo", type=Path, help="Path to logo image (PNG/SVG)")
    args = parser.parse_args()

    # Resolve benchmark source
    if args.latest:
        benchmark_path = find_latest_benchmark()
        console.print(f"[cyan]Using latest benchmark: {benchmark_path.name}[/cyan]")
    elif args.benchmark:
        benchmark_path = args.benchmark
        if not benchmark_path.exists():
            console.print(f"[red]Benchmark file not found: {benchmark_path}[/red]")
            sys.exit(1)
    else:
        parser.error("Specify --benchmark <file> or --latest")

    # Load data
    data = load_benchmark(benchmark_path)
    metrics = extract_metrics(data)

    if not metrics:
        console.print("[yellow]Warning: No metrics extracted from benchmark.[/yellow]")

    # Build subtitle
    subtitle = args.subtitle
    if not subtitle:
        version = data.get("version", "")
        date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
        subtitle = (
            f"Benchmark Results — v{version} • {date}" if version else f"Benchmark Results — {date}"
        )

    # Render
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    card = TweetCard(theme=args.theme)
    card.render(
        title=args.title,
        subtitle=subtitle,
        metrics=metrics,
        footer="github.com/your-org/skills-primitive",
        output_path=args.output,
        logo_path=args.logo,
    )

    # Print summary
    size_kb = args.output.stat().st_size / 1024
    console.print(f"[green]Card generated: {args.output} ({size_kb:.1f} KB)[/green]")
    console.print(f"[dim]Dimensions: {CARD_WIDTH}×{CARD_HEIGHT}px | Theme: {args.theme}[/dim]")


if __name__ == "__main__":
    main()
