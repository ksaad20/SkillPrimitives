# SkillPrimitives

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Linux](https://img.shields.io/badge/Linux-FCC624?logo=linux&logoColor=black)
![macOS](https://img.shields.io/badge/macOS-000000?logo=apple&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-0078D6?logo=windows&logoColor=white)
![Tests](https://github.com/ksaad20/SkillPrimitives/actions/workflows/ci.yml/badge.svg)
[![codecov](https://codecov.io/gh/ksaad20/SkillPrimitives/branch/main/graph/badge.svg)](https://codecov.io/gh/ksaad20/SkillPrimitives)

# For collaborators
pip install -e ".[dev]"

# For early testers who want to try it
pip install "skill-primitives @ git+https://github.com/ksaad20/SkillPrimitives.git@main"

# SkillPrimitives
A natural language to robot motion transformer. Decompose LeRobot datasets into composable skills, then generate manipulation trajectories from plain English.

# Skill Primitives

Natural language to robot motion. Built on LeRobot.

Decompose robotics training datasets into composable skill primitives and annotate them with natural language instructions.

## What It Does

- **Segment**: Splits LeRobot episode trajectories into discrete primitives (reach, grasp, lift, place, transport) using gripper state and motion heuristics
- **Annotate**: Labels each primitive with a natural language command using local LLMs or API providers
- **Compose**: Chains primitives into task sequences via a Python API for downstream training or execution

## Quick Start

```python
from skill_primitives import segment_episode, compose

# Split a LeRobot episode into primitives
primitives = segment_episode("lerobot/pusht", episode=0)

# Compose a task sequence
task = compose([
    "reach the red target",
    "grasp firmly", 
    "lift 5cm",
    "place in the green zone"
])

# Export for your training pipeline
task.export_json("task.json")

```

Install

```

git clone https://github.com/YOU/skill-primitives.git
cd skill-primitives
pip install -e .

```

LLM annotation install Ollama or set your Groq API key:

```

git clone https://github.com/YOU/skill-primitives.git
cd skill-primitives
pip install -e .

```

Usage 

Segment a dataset

```

python -m skill_primitives.segment \
  --dataset lerobot/pusht \
  --output ./my_skills/

```

Produces

```

my_skills/
├── reach/
│   ├── episode_000_seg_001.parquet
│   └── metadata.yaml
├── grasp/
│   ├── episode_000_seg_002.parquet
│   └── metadata.yaml
...

```

Annotate with Natural Language 

```

python -m skill_primitives.annotate \
  --input ./my_skills/ \
  --provider ollama \
  --model llama3.1

```

Updates each metadata with:

```

description: "grasp the red cube firmly"

```
Compose in python 

```

from skill_primitives import SkillLibrary, compose

lib = SkillLibrary.from_disk("./my_skills/")
sequence = compose([
    "reach the object",
    "grasp",
    "lift",
    "place gently"
], library=lib)

# Export trajectory for training or playback
sequence.export_json("my_task.json")
sequence.export_lerobot("my_task.parquet")

```

Architecture 

```

skill_primitives/
├── core/
│   ├── segmenter.py          # Heuristic trajectory segmentation
│   ├── annotator.py          # LLM skill description
│   └── composer.py           # Skill sequencing API
├── primitives/
│   ├── base.py               # Extensible Primitive base class
│   ├── reach.py
│   ├── grasp.py
│   ├── lift.py
│   ├── transport.py
│   └── place.py
├── io/
│   ├── lerobot_adapter.py    # LeRobot dataset loading
│   └── exporters.py          # JSON, Parquet, LeRobot format
└── cli/
    ├── segment.py
    └── annotate.py

```
Adding a new primitive: Subclass Primitive in primitives/base.py and implement detect() and validate().

Adding a new dataset format: Implement BaseAdapter in io/base.py.

CLI Reference

Table

```

| Command    | Description                               |
| ---------- | ----------------------------------------- |
| `segment`  | Extract primitives from LeRobot episodes  |
| `annotate` | Generate NL descriptions for each segment |

```

Requirements

```
Python 3.9+
PyTorch
datasets (HuggingFace)
lerobot (optional, for direct dataset loading)

```
License

```
Apache 2.0
