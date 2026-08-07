# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Scaffold for `insert` and `screw` primitives (see `primitives/`).
- Placeholder ROS2 integration module (`io/ros2_adapter.py` — planned for v0.2.0).

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A

---

## [0.0.1] — 2026-08-07

### Added
- **Core segmentation engine** (`core/segmenter.py`): Heuristic trajectory segmentation for LeRobot datasets. Splits episodes into discrete primitives using gripper state transitions and motion heuristics.
- **Five foundational primitives**: `reach`, `grasp`, `lift`, `transport`, `place`. Each implements `detect()`, `validate()`, and `describe()` via the extensible `Primitive` base class.
- **Natural language annotation** (`core/annotator.py`): LLM-driven skill description generation. Supports Ollama (local), Groq, and OpenAI providers out of the box.
- **Skill composition API** (`core/composer.py`): Chain primitives into novel task sequences using plain English instructions. Exports to JSON and LeRobot Parquet formats.
- **LeRobot dataset adapter** (`io/lerobot_adapter.py`): Load and standardize episodes from any HuggingFace LeRobot dataset.
- **CLI tools**: Four entry points — `sp-segment`, `sp-annotate`, `sp-compose`, `sp-demo`. Zero-config usage for common workflows.
- **Interactive demo** (`cli/demo.py`): 10-second hello-world script. Segments a sample episode, composes a novel task, and exports to JSON. Runs on CPU.
- **Pre-computed skill zoo** (`zoo/`): Directory structure and download script for hosting segmented skill libraries on HuggingFace.
- **Benchmark scaffolding** (`benchmarks/`): Standardized task definitions, success-rate metrics, and baseline comparison framework.
- **HuggingFace Space** (`spaces/app.py`): Gradio demo for interactive segmentation and composition. Deployable to Spaces with one command.
- **Paper reproducibility suite** (`paper/reproduce_all.py`): One-command regeneration of all figures and tables from the JOSS submission.
- **Full test suite** (`tests/`): 12 tests covering segmentation, composition, exporters, and zoo integrity. CI runs on Python 3.9–3.12.
- **GitHub Actions CI** (`.github/workflows/test.yml`): Quality checks (black, ruff, mypy), fast test matrix, package build verification, and demo smoke tests.
- **Developer tooling**: `pyproject.toml` with `[dev]` extras, `Makefile`, `.pre-commit-config.yaml`, and `CITATION.cff` for one-click academic citation.
- **Documentation**: `README.md` (landing page), `docs/WHY.md` (manifesto), `docs/PRIMITIVES.md` (visual catalog), `docs/CONTRIBUTING.md` (20-minute contributor guide), `docs/ROADMAP.md` (public roadmap).

### Notes
- This is an **alpha release**. APIs are stable enough for experimentation but may evolve based on community feedback.
- Only **LeRobot-compatible datasets** are supported out of the box. Custom robot adapters require subclassing `BaseAdapter`.
- The `export_lerobot()` method is a stub; full Parquet schema alignment is targeted for v0.0.2.
- LLM annotation defaults to template-based fallback if no API key or local model is configured.

---

## [0.0.0] — 2026-08-01

### Added
- Repository bootstrap (`bootstrap.py`). Generates the entire project structure from a single script.
- Initial architecture design and community validation.
