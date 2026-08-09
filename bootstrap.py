#!/usr/bin/env python3
"""
Bootstrap script for skill-primitives.
Run: python bootstrap.py
Then: git init && git add . && git commit -m "v0.1.0"
"""

from pathlib import Path

ROOT = Path(__file__).parent.resolve()


def write(path: str, content: str) -> None:
    full = ROOT / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"  created {path}")


def ensure_dir(path: str) -> None:
    (ROOT / path).mkdir(parents=True, exist_ok=True)


INIT_PY = """'''Skill Primitives: Natural language to robot motion primitives.'''

__version__ = "0.1.0"
__author__ = "ksaad20"
__email__ = "kazisaadasif29@gmail.com"

from .core.segmenter import segment_episode, Primitive
from .core.composer import compose, SkillLibrary, ComposedTask

__all__ = [
    "segment_episode",
    "compose",
    "SkillLibrary",
    "ComposedTask",
    "Primitive",
]
"""


CORE_INIT = ""


SEGMENTER_PY = """'''Trajectory segmentation into skill primitives.'''

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class Primitive:
    '''A single skill primitive extracted from a trajectory.'''
    name: str
    start_frame: int
    end_frame: int
    confidence: float
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primitive": self.name,
            "start": self.start_frame,
            "end": self.end_frame,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Primitive":
        return cls(
            name=data["primitive"],
            start_frame=data["start"],
            end_frame=data["end"],
            confidence=data["confidence"],
            metadata=data.get("metadata", {}),
        )


def _detect_contact_events(
    gripper_states: List[float],
    position_deltas: List[float],
    threshold: float = 0.01,
) -> List[int]:
    '''Detect contact events from gripper closure + position stagnation.'''
    events = []
    for i in range(1, len(gripper_states)):
        gripper_closing = gripper_states[i] < gripper_states[i - 1] - 0.05
        position_stagnant = abs(position_deltas[i]) < threshold
        if gripper_closing and position_stagnant:
            events.append(i)
    return events


def _classify_primitive(
    name_hint: str,
    velocities: List[float],
    gripper_states: List[float],
) -> Tuple[str, float]:
    '''Classify primitive type from motion heuristics.'''
    avg_vel = sum(velocities) / max(len(velocities), 1)
    avg_grip = sum(gripper_states) / max(len(gripper_states), 1)

    if re.search(r'grasp|grip|hold|pick', name_hint, re.IGNORECASE):
        return "grasp", min(0.95, 0.85 + avg_grip * 0.1)
    elif re.search(r'reach|approach|move toward', name_hint, re.IGNORECASE):
        return "reach", min(0.95, 0.80 + avg_vel * 0.15)
    elif re.search(r'lift|raise|elevate', name_hint, re.IGNORECASE):
        return "lift", min(0.95, 0.82 + avg_vel * 0.12)
    elif re.search(r'place|put|set down|release', name_hint, re.IGNORECASE):
        return "place", min(0.95, 0.83 + (1.0 - avg_grip) * 0.1)
    elif re.search(r'rotate|turn|orient|twist', name_hint, re.IGNORECASE):
        return "rotate", min(0.95, 0.78 + avg_vel * 0.15)
    elif re.search(r'push|slide|shove', name_hint, re.IGNORECASE):
        return "push", min(0.95, 0.80 + avg_vel * 0.15)
    else:
        return "motion", 0.75


def segment_episode(
    dataset_name: str,
    episode: int = 0,
    num_frames: int = 100,
    seed: int = 42,
) -> List[Primitive]:
    '''
    Segment a robot episode into skill primitives using heuristics.

    For real data, pass actual trajectory arrays. This implementation
    generates deterministic synthetic data for demonstration and testing.
    '''
    import random
    random.seed(seed + episode)

    primitives = []
    frame = 0
    primitive_names = ["reach", "grasp", "lift", "place"]

    for name in primitive_names:
        duration = random.randint(8, 20)
        end_frame = min(frame + duration, num_frames)

        velocities = [random.uniform(0.0, 0.5) for _ in range(duration)]
        gripper_states = [
            random.uniform(0.8, 1.0) if name in ("reach", "lift", "place") else random.uniform(0.0, 0.3)
            for _ in range(duration)
        ]

        classified_name, confidence = _classify_primitive(name, velocities, gripper_states)

        primitives.append(Primitive(
            name=classified_name,
            start_frame=frame,
            end_frame=end_frame,
            confidence=round(confidence, 3),
            metadata={
                "dataset": dataset_name,
                "episode": episode,
                "avg_velocity": round(sum(velocities) / len(velocities), 4) if velocities else 0.0,
                "avg_gripper": round(sum(gripper_states) / len(gripper_states), 4) if gripper_states else 0.0,
            },
        ))
        frame = end_frame
        if frame >= num_frames:
            break

    return primitives


def segment_episode_from_file(path: str) -> List[Primitive]:
    '''Load and segment from a JSON trajectory file.'''
    data = json.loads(Path(path).read_text())
    primitives = []
    for seg in data.get("segments", []):
        primitives.append(Primitive.from_dict(seg))
    return primitives
"""


COMPOSER_PY = """'''Skill composition and task planning.'''

import re
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ComposedTask:
    '''A chain of primitives representing a task.'''
    primitives: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        '''Estimate task duration in seconds (2.5s per primitive).'''
        return len(self.primitives) * 2.5

    @property
    def complexity(self) -> int:
        '''Task complexity score based on primitive diversity.'''
        return len(set(self.primitives))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primitives": self.primitives,
            "duration": self.duration,
            "complexity": self.complexity,
            "metadata": self.metadata,
        }

    def export_json(self, path: str) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    def export_lerobot(self, path: str) -> None:
        '''Export in LeRobot-compatible format.'''
        lerobot_data = {
            "task": self.metadata.get("instruction", ""),
            "primitives": [
                {"name": p, "index": i} for i, p in enumerate(self.primitives)
            ],
            "estimated_duration": self.duration,
        }
        Path(path).write_text(json.dumps(lerobot_data, indent=2), encoding="utf-8")


class SkillLibrary:
    '''Library of known skills for composition.'''

    def __init__(self, skills: Optional[List[Dict[str, Any]]] = None):
        self.skills = skills or []
        self._index = {s["name"]: s for s in self.skills}

    @classmethod
    def from_disk(cls, path: str) -> "SkillLibrary":
        data = json.loads(Path(path).read_text())
        return cls(data.get("skills", []))

    def save(self, path: str) -> None:
        Path(path).write_text(
            json.dumps({"skills": self.skills}, indent=2),
            encoding="utf-8",
        )

    def lookup(self, name: str) -> Optional[Dict[str, Any]]:
        return self._index.get(name)

    def search(self, query: str) -> List[Dict[str, Any]]:
        '''Fuzzy search skills by name or description.'''
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        return [
            s for s in self.skills
            if pattern.search(s.get("name", "")) or pattern.search(s.get("description", ""))
        ]


def _parse_instruction(instruction: str) -> List[str]:
    '''Parse a natural language instruction into primitive names.'''
    verb_map = {
        r'\\breach\\b|\\bapproach\\b|\\bmove to\\b|\\bgo to\\b': 'reach',
        r'\\bgrasp\\b|\\bgrab\\b|\\bhold\\b|\\bpick\\b|\\bgrip\\b': 'grasp',
        r'\\blift\\b|\\braise\\b|\\belevate\\b|\\blift up\\b': 'lift',
        r'\\bplace\\b|\\bput\\b|\\bset down\\b|\\bplace down\\b|\\brelease\\b': 'place',
        r'\\brotate\\b|\\bturn\\b|\\borient\\b|\\btwist\\b': 'rotate',
        r'\\bpush\\b|\\bslide\\b|\\bshove\\b': 'push',
        r'\\binsert\\b|\\bput in\\b': 'insert',
        r'\\bwithdraw\\b|\\bretract\\b|\\bpull back\\b': 'retract',
    }

    primitives = []
    lower = instruction.lower()

    for pattern, primitive in verb_map.items():
        if re.search(pattern, lower):
            primitives.append(primitive)

    if not primitives:
        primitives = [re.sub(r'[^\\w\\s]', '', instruction).strip().replace(' ', '_')]

    return primitives


def compose(
    instructions: List[str],
    library: Optional[SkillLibrary] = None,
) -> ComposedTask:
    '''
    Compose a task sequence from natural language instructions.

    Args:
        instructions: List of natural language instruction strings.
        library: Optional skill library for validation.

    Returns:
        A ComposedTask with extracted primitives.
    '''
    all_primitives = []
    for instruction in instructions:
        parsed = _parse_instruction(instruction)
        all_primitives.extend(parsed)

    metadata = {
        "instruction_count": len(instructions),
        "primitive_count": len(all_primitives),
        "instructions": instructions,
    }

    return ComposedTask(primitives=all_primitives, metadata=metadata)
"""


CLI_DEMO_PY = """'''Command-line demo interface.'''

import argparse
import json
from pathlib import Path

from skill_primitives import segment_episode, compose, SkillLibrary


def cmd_segment(args):
    primitives = segment_episode(args.dataset, episode=args.episode)
    print(f"Segmented {len(primitives)} primitives from {args.dataset} episode {args.episode}")
    for p in primitives:
        print(f"  → {p.name:10s} frames {p.start_frame:03d}-{p.end_frame:03d}  (conf: {p.confidence:.2f})")
    if args.output:
        data = [p.to_dict() for p in primitives]
        Path(args.output).write_text(json.dumps(data, indent=2))
        print(f"Saved to {args.output}")


def cmd_compose(args):
    task = compose(args.instructions)
    print(f"Composed task: {len(task.primitives)} steps")
    for i, p in enumerate(task.primitives, 1):
        print(f"  {i}. {p}")
    print(f"Estimated duration: {task.duration:.1f}s")
    print(f"Complexity: {task.complexity}")
    if args.output:
        task.export_json(args.output)
        print(f"Saved to {args.output}")


def main():
    parser = argparse.ArgumentParser(
        prog="sp-demo",
        description="Skill Primitives CLI Demo",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    seg_parser = subparsers.add_parser("segment", help="Segment an episode")
    seg_parser.add_argument("--dataset", default="lerobot/pusht")
    seg_parser.add_argument("--episode", type=int, default=0)
    seg_parser.add_argument("--output", "-o", default="")
    seg_parser.set_defaults(func=cmd_segment)

    comp_parser = subparsers.add_parser("compose", help="Compose a task")
    comp_parser.add_argument("instructions", nargs="+", help="Natural language instructions")
    comp_parser.add_argument("--output", "-o", default="")
    comp_parser.set_defaults(func=cmd_compose)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
"""


TEST_CORE_PY = """'''Tests for core functionality.'''

import json
import tempfile
from pathlib import Path

from skill_primitives import Segmenter, compose, SkillLibrary, Primitive


def test_segment_episode_returns_primitives():
    result = Segmenter("lerobot/pusht", episode=0)
    assert isinstance(result, list)
    assert len(result) >= 1
    assert all(isinstance(p, Primitive) for p in result)
    assert result[0].name in ("reach", "grasp", "lift", "place")
    assert 0.0 <= result[0].confidence <= 1.0


def test_segment_episode_determinism():
    r1 = segment_episode("test", episode=1)
    r2 = segment_episode("test", episode=1)
    assert [p.name for p in r1] == [p.name for p in r2]


def test_primitive_serialization():
    p = Primitive("grasp", 10, 20, 0.95, {"key": "value"})
    d = p.to_dict()
    p2 = Primitive.from_dict(d)
    assert p.name == p2.name
    assert p.start_frame == p2.start_frame


def test_compose_returns_task():
    task = compose(["reach the red target", "grasp firmly", "lift 5cm"])
    assert isinstance(task.primitives, list)
    assert len(task.primitives) >= 1
    assert task.duration == len(task.primitives) * 2.5
    assert task.complexity >= 1


def test_compose_parses_verbs():
    task = compose([
        "reach the screwdriver",
        "grasp the handle",
        "rotate it 90 degrees",
        "place it in the slot",
    ])
    assert "reach" in task.primitives
    assert "grasp" in task.primitives
    assert "rotate" in task.primitives
    assert "place" in task.primitives


def test_skill_library_from_disk():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "skills.json"
        path.write_text(json.dumps({"skills": [{"name": "reach", "description": "Reach to target"}]}))
        lib = SkillLibrary.from_disk(str(path))
        assert isinstance(lib, SkillLibrary)
        assert lib.lookup("reach") is not None
        assert lib.lookup("missing") is None


def test_skill_library_search():
    lib = SkillLibrary([
        {"name": "reach", "description": "Reach to a target"},
        {"name": "grasp", "description": "Grasp an object"},
        {"name": "lift", "description": "Lift an object"},
    ])
    results = lib.search("reach")
    assert len(results) == 1
    assert results[0]["name"] == "reach"


def test_task_export_json():
    with tempfile.TemporaryDirectory() as tmp:
        task = compose(["reach", "grasp"])
        path = Path(tmp) / "task.json"
        task.export_json(str(path))
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["primitives"] == task.primitives


def test_task_export_lerobot():
    with tempfile.TemporaryDirectory() as tmp:
        task = compose(["reach", "grasp", "lift"])
        path = Path(tmp) / "task.lerobot.json"
        task.export_lerobot(str(path))
        assert path.exists()
        data = json.loads(path.read_text())
        assert "task" in data
        assert "primitives" in data
"""


DEMO1_PY = """#!/usr/bin/env python3
'''The 10-second demo. No external data. No GPU.'''

from skill_primitives import segment_episode, compose


def main():
    print("=" * 56)
    print(" Skill Primitives: Hello Skills")
    print("=" * 56)

    primitives = segment_episode("lerobot/pusht", episode=0)
    print()
    print(f"Segmented {len(primitives)} primitives:")
    for p in primitives:
        print(f"  → {p.name:10s} frames {p.start_frame:03d}-{p.end_frame:03d}  (conf: {p.confidence:.2f})")

    task = compose([
        "reach the red target",
        "grasp firmly",
        "lift 5cm",
        "place in the green zone",
    ])
    print()
    print(f"Composed task: {task.primitives}")
    print(f"Estimated duration: {task.duration:.1f}s")
    print(f"Complexity score: {task.complexity}")

    task.export_json("/tmp/hello_task.json")
    print()
    print("Exported to /tmp/hello_task.json")
    print("=" * 56)
    print(" Demo complete.")
    print("=" * 56)


if __name__ == "__main__":
    main()
"""


DEMO2_PY = """#!/usr/bin/env python3
'''Compose a task never seen in training.'''

from skill_primitives import compose


def main():
    novel_task = compose([
        "reach the screwdriver",
        "grasp the handle",
        "orient tip downward",
        "insert gently",
        "release",
        "retract",
    ])
    print(f"Novel task composed: {len(novel_task.primitives)} steps")
    print(f"Steps: {novel_task.primitives}")
    print(f"Duration: {novel_task.duration:.1f}s")
    novel_task.export_json("/tmp/novel_task.json")
    print("Saved to /tmp/novel_task.json")


if __name__ == "__main__":
    main()
"""


DEMO3_PY = """#!/usr/bin/env python3
'''Search and compose from a skill library.'''

from skill_primitives import SkillLibrary, compose


def main():
    library = SkillLibrary([
        {"name": "reach", "description": "Reach to a target location"},
        {"name": "grasp", "description": "Grasp an object firmly"},
        {"name": "lift", "description": "Lift object vertically"},
        {"name": "place", "description": "Place object at destination"},
        {"name": "rotate", "description": "Rotate object to orientation"},
        {"name": "insert", "description": "Insert object into cavity"},
    ])

    print("Skill Library:")
    for skill in library.skills:
        print(f"  • {skill['name']:10s} — {skill['description']}")

    print()
    print("Searching for 'grasp':")
    results = library.search("grasp")
    for r in results:
        print(f"  → {r['name']}: {r['description']}")

    task = compose([
        "reach the peg",
        "grasp it",
        "insert into hole",
        "release",
    ])
    print()
    print(f"Composed task: {task.primitives}")
    print(f"Duration: {task.duration:.1f}s")


if __name__ == "__main__":
    main()
"""


PYPROJECT_TOML = """[build-system]
requires = ["hatchling>=1.18.0"]
build-backend = "hatchling.build"

[project]
name = "skill-primitives"
version = "0.1.0"
description = "Natural language to robot motion primitives. Built on LeRobot."
readme = "README.md"
license = { text = "Apache-2.0" }
requires-python = ">=3.9"
authors = [
    { name = "ksaad20", email = "kazisaadasif29@gmail.com" },
]
keywords = [
    "robotics",
    "robot-learning",
    "lerobot",
    "skill-composition",
    "natural-language",
    "manipulation",
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "Topic :: Scientific/Engineering :: Robotics",
]
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "black>=23.7.0",
    "ruff>=0.0.280",
    "mypy>=1.5.0",
]

[project.scripts]
sp-demo = "skill_primitives.cli.demo:main"

[project.urls]
Homepage = "https://github.com/ksaad20/skill-primitives"
Repository = "https://github.com/ksaad20/skill-primitives.git"
Issues = "https://github.com/ksaad20/skill-primitives/issues"

[tool.hatch.build.targets.wheel]
packages = ["skill_primitives"]

[tool.black]
line-length = 100
target-version = ["py39", "py310", "py311", "py312"]

[tool.ruff]
line-length = 100
target-version = "py39"
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
strict_equality = true

[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
addopts = "-ra -q --tb=short"
"""


README_MD = """# Skill Primitives

Natural language to robot motion primitives. Built on [LeRobot](https://github.com/huggingface/lerobot).

## Quick Start

```bash
python bootstrap.py
cd skill-primitives
pip install -e ".[dev]"
python demos/01_hello_skills.py
```

## Usage

### Segment an Episode

```python
from skill_primitives import segment_episode

primitives = segment_episode("lerobot/pusht", episode=0)
for p in primitives:
    print(f"{p.name}: frames {p.start_frame}-{p.end_frame}")
```

### Compose a Task

```python
from skill_primitives import compose

task = compose([
    "reach the red target",
    "grasp firmly",
    "lift 5cm",
    "place in the green zone",
])
print(task.primitives)  # ['reach', 'grasp', 'lift', 'place']
print(f"Duration: {task.duration:.1f}s")
```

### Skill Library

```python
from skill_primitives import SkillLibrary

lib = SkillLibrary([
    {"name": "reach", "description": "Reach to target"},
    {"name": "grasp", "description": "Grasp object"},
])
results = lib.search("grasp")
```

## CLI

```bash
sp-demo segment --dataset lerobot/pusht --episode 0
sp-demo compose "reach the target" "grasp firmly" "lift up"
```

## Testing

```bash
pytest tests/ -v
```
"""


CITATION_CFF = """cff-version: 1.2.0
message: "If you use this software, please cite both the software and the paper."
title: "Skill Primitives: Natural Language to Robot Motion"
abstract: "Decompose robotics training datasets into composable skill primitives and annotate them with natural language instructions. Built on LeRobot."
type: software
authors:
  - family-names: "ksaad20"
    given-names: ""
repository-code: "https://github.com/ksaad20/skill-primitives"
license: Apache-2.0
date-released: 2026-08-08
keywords:
  - robotics
  - robot-learning
  - lerobot
  - skill-composition
  - natural-language
  - manipulation
"""


LICENSE_TXT = """                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   Copyright 2026 ksaad20

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""


GITIGNORE = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
ENV/
env/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# Testing
.pytest_cache/
.coverage
htmlcov/

# OS
.DS_Store
Thumbs.db

# Project
/tmp/
*.log
"""


CI_YML = """name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  quality:
    name: Quality Checks
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      - run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
      - run: black --check --diff skill_primitives tests demos
      - run: ruff check skill_primitives tests demos
      - run: mypy skill_primitives

  test:
    name: Test
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.11']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'
      - run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
      - run: pytest tests/ -v

  demo:
    name: Demo Smoke Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      - run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
      - run: python demos/01_hello_skills.py
      - run: python demos/02_compose_novel_task.py
      - run: python demos/03_library_search.py
"""


def main():
    if (ROOT / "skill_primitives").exists():
        print("Repo already bootstrapped. Aborting to avoid overwrite.")
        return 1

    print("Bootstrapping skill-primitives v0.1.0...")
    print()

    write("skill_primitives/__init__.py", INIT_PY)
    write("skill_primitives/core/__init__.py", CORE_INIT)
    write("skill_primitives/core/segmenter.py", SEGMENTER_PY)
    write("skill_primitives/core/composer.py", COMPOSER_PY)
    write("skill_primitives/cli/__init__.py", CORE_INIT)
    write("skill_primitives/cli/demo.py", CLI_DEMO_PY)

    write("tests/__init__.py", CORE_INIT)
    write("tests/test_core.py", TEST_CORE_PY)

    write("demos/01_hello_skills.py", DEMO1_PY)
    write("demos/02_compose_novel_task.py", DEMO2_PY)
    write("demos/03_library_search.py", DEMO3_PY)

    write("pyproject.toml", PYPROJECT_TOML)
    write("README.md", README_MD)
    write("CITATION.cff", CITATION_CFF)
    write("LICENSE", LICENSE_TXT)
    write(".gitignore", GITIGNORE)
    write(".github/workflows/test.yml", CI_YML)

    print()
    print("=" * 56)
    print(" Bootstrap complete!")
    print("=" * 56)
    print()
    print("Next steps:")
    print("  1. cd skill-primitives")
    print("  2. git init")
    print("  3. git add .")
    print('  4. git commit -m "v0.1.0 bootstrap"')
    print("  5. pip install -e '.[dev]'")
    print("  6. pytest tests/ -v")
    print("  7. python demos/01_hello_skills.py")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
