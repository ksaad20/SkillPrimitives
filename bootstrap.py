#!/usr/bin/env python3
"""
Bootstrap script for skill-primitives MVP.
Run once: python bootstrap.py
Then: git init && git add . && git commit -m "v0.0.1 bootstrap"
Then: git push
CI will be green on first run.
"""
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))


def write(path, content):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(content.strip() + "\n")
    print(f"  created {path}")


def main():
    if os.path.exists(os.path.join(ROOT, "skill_primitives")):
        print("Repo already bootstrapped. Aborting to avoid overwrite.")
        return

    print("Bootstrapping skill-primitives MVP...")

    # =========================================================================
    # 1. CORE PACKAGE (no external references)
    # =========================================================================

    write("skill_primitives/__init__.py", '''
__version__ = "0.0.1"

from .core.segmenter import segment_episode
from .core.composer import compose, SkillLibrary

__all__ = ["segment_episode", "compose", "SkillLibrary"]
''')

    write("skill_primitives/core/__init__.py", "")

    write("skill_primitives/core/segmenter.py", '''
"""Heuristic trajectory segmentation."""

from typing import List, Dict, Any
import numpy as np


def segment_episode(dataset_name: str, episode: int = 0) -> List[Dict[str, Any]]:
    """
    Stub: Segment a LeRobot episode into primitives.
    Returns a list of primitive dicts for MVP demo purposes.
    """
    # MVP stub: return synthetic primitives so the API works immediately
    return [
        {"primitive": "reach", "start": 0, "end": 10, "confidence": 0.95},
        {"primitive": "grasp", "start": 10, "end": 15, "confidence": 0.92},
        {"primitive": "lift", "start": 15, "end": 25
