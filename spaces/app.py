#!/usr/bin/env python3
"""Hugging Face Space: Interactive Skill Primitives Demo.

Gradio app for visual segmentation and composition of robot skills.
Deploy to HF Spaces with: huggingface-cli upload
"""

from __future__ import annotations

import json
import tempfile

import gradio as gr

from skill_primitives import compose, segment_episode
from skill_primitives.core.annotator import Annotator


def segment_dataset(dataset_name: str, episode: int) -> tuple[str, str]:
    """Segment an episode and return formatted output.

    Returns:
        Tuple of (markdown table, raw JSON).
    """
    try:
        primitives = segment_episode(dataset_name, episode=episode)
    except Exception as e:
        return f"**Error:** {e}", "{}"

    if not primitives:
        return "No primitives detected.", "{}"

    # Build markdown table
    lines = [
        "| # | Type | Frames | Confidence |",
        "|---|---|------|--------|------------|",
    ]
    for i, p in enumerate(primitives):
        lines.append(
            f"| {i + 1} | `{p['type']}` | {p['start']}-{p['end']} | {p['confidence']:.2f} |"
        )

    return "\n".join(lines), json.dumps(primitives, indent=2)


def annotate_primitives_json(primitives_json: str, provider: str, model: str) -> str:
    """Annotate primitives with natural language.

    Args:
        primitives_json: JSON string of primitives.
        provider: LLM provider name.
        model: Model name.

    Returns:
        Markdown formatted annotated primitives.
    """
    try:
        primitives = json.loads(primitives_json)
    except json.JSONDecodeError:
        return "Invalid JSON. Please segment a dataset first."

    if not primitives:
        return "No primitives to annotate."

    annotator = Annotator(provider=provider, model=model)
    annotated = annotator.annotate_batch(primitives)

    lines = [
        "| # | Type | Description |",
        "|---|---|------|-------------|",
    ]
    for i, p in enumerate(annotated):
        desc = p.get("description", "—")
        lines.append(f"| {i + 1} | `{p['type']}` | {desc} |")

    return "\n".join(lines)


def compose_task(instructions_text: str) -> tuple[str, str]:
    """Compose a task from natural language instructions.

    Args:
        instructions_text: One instruction per line.

    Returns:
        Tuple of (markdown output, JSON export).
    """
    instructions = [line.strip() for line in instructions_text.splitlines() if line.strip()]

    if not instructions:
        return "Please enter at least one instruction.", "{}"

    task = compose(instructions)

    lines = [
        f"**Composed {len(task.skills)} primitives** (est. duration: {task.duration:.1f}s)",
        "",
        "| # | Type | Instruction |",
        "|---|---|------|-------------|",
    ]
    for i, p in enumerate(task.primitives, 1):
        lines.append(f"| {i} | `{p['type']}` | {p['instruction']} |")

    # Generate JSON export
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        task.export_json(tmp.name)

    with open(tmp.name) as f:
        export_json = f.read()

    return "\n".join(lines), export_json


def visualize_primitive_distribution(primitives_json: str) -> str:
    """Generate a simple text-based bar chart of primitive types.

    Args:
        primitives_json: JSON string of primitives.

    Returns:
        ASCII bar chart.
    """
    try:
        primitives = json.loads(primitives_json)
    except json.JSONDecodeError:
        return "No data to visualize."

    if not primitives:
        return "No primitives to visualize."

    counts = {}
    for p in primitives:
        ptype = p.get("type", "unknown")
        counts[ptype] = counts.get(ptype, 0) + 1

    max_count = max(counts.values()) if counts else 1
    lines = ["**Primitive Distribution**", ""]

    for ptype in sorted(counts.keys()):
        count = counts[ptype]
        bar = "█" * int((count / max_count) * 20)
        lines.append(f"`{ptype:10s}` | {bar} {count}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

with gr.Blocks(title="Skill Primitives") as demo:
    gr.Markdown("# 🦾 Skill Primitives")
    gr.Markdown(
        "**Natural Language to Robot Motion** — Decompose LeRobot datasets "
        "into composable skills and chain them into new tasks."
    )

    # State to pass primitives between tabs
    primitives_state = gr.State("[]")

    with gr.Tab("1. Segment"):
        gr.Markdown("Extract skill primitives from a LeRobot dataset.")

        with gr.Row():
            dataset_input = gr.Textbox(
                value="lerobot/pusht",
                label="Dataset",
                placeholder="lerobot/pusht",
            )
            episode_input = gr.Number(
                value=0,
                label="Episode",
                precision=0,
            )

        segment_btn = gr.Button("Segment Episode", variant="primary")

        segment_output = gr.Markdown(label="Detected Primitives")
        segment_json = gr.JSON(label="Raw Output", visible=False)

        segment_btn.click(
            fn=segment_dataset,
            inputs=[dataset_input, episode_input],
            outputs=[segment_output, primitives_state],
        )

    with gr.Tab("2. Annotate"):
        gr.Markdown("Label primitives with natural language descriptions.")

        with gr.Row():
            provider_input = gr.Dropdown(
                choices=["ollama", "groq", "openai"],
                value="ollama",
                label="Provider",
            )
            model_input = gr.Textbox(
                value="llama3.1",
                label="Model",
            )

        annotate_btn = gr.Button("Annotate", variant="primary")
        annotate_output = gr.Markdown(label="Annotated Primitives")

        annotate_btn.click(
            fn=annotate_primitives_json,
            inputs=[primitives_state, provider_input, model_input],
            outputs=annotate_output,
        )

    with gr.Tab("3. Compose"):
        gr.Markdown("Chain primitives into a novel task sequence.")

        instructions_input = gr.TextArea(
            value="reach the red cube\ngrasp firmly\nlift 5cm\nplace in blue bin",
            label="Instructions (one per line)",
            lines=6,
        )

        compose_btn = gr.Button("Compose Task", variant="primary")
        compose_output = gr.Markdown(label="Composed Task")
        compose_json = gr.Code(label="JSON Export", language="json")

        compose_btn.click(
            fn=compose_task,
            inputs=instructions_input,
            outputs=[compose_output, compose_json],
        )

    with gr.Tab("4. Visualize"):
        gr.Markdown("Visualize primitive distribution.")

        viz_btn = gr.Button("Generate Chart", variant="primary")
        viz_output = gr.Markdown(label="Distribution")

        viz_btn.click(
            fn=visualize_primitive_distribution,
            inputs=primitives_state,
            outputs=viz_output,
        )

    gr.Markdown("---")
    gr.Markdown(
        "[GitHub](https://github.com/YOUR_USERNAME/skill-primitives) | "
        "[Docs](https://github.com/YOUR_USERNAME/skill-primitives#readme)"
    )

if __name__ == "__main__":
    demo.launch()
