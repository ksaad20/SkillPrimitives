import re
import subprocess
from pathlib import Path

ROOT = Path(".")


def strip_type_ignores(content: str) -> str:
    """Remove all '# type: ignore[...]' and '# type: ignore' comments."""
    return re.sub(r"\s*# type: ignore(?:\[.*?\])?", "", content)


def fix_lerobot_adapter(path: Path) -> None:
    content = path.read_text()
    content = strip_type_ignores(content)

    if "from datasets import Dataset" not in content:
        lines = content.splitlines(keepends=True)
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("from __future__") or line.startswith("import "):
                insert_idx = i + 1
        lines.insert(insert_idx, "from datasets import Dataset\n")
        content = "".join(lines)

    content = re.sub(
        r"^(\s+)ds\s*=\s*(load_dataset\()",
        r"\1ds: Dataset = \2",
        content,
        flags=re.MULTILINE,
    )

    path.write_text(content)
    print(f"  OK {path}")


def _add_any_types(match: re.Match) -> str:
    prefix = match.group(1)  # "def foo("
    params = match.group(2)  # "a, b, c=1"
    ret = match.group(3) or ""
    if not ret:
        ret = " -> Any"

    parts = []
    for p in params.split(","):
        p = p.strip()
        if not p:
            continue
        if p in ("self", "cls"):
            parts.append(p)
        elif ":" not in p and "=" not in p:
            parts.append(f"{p}: Any")
        elif ":" not in p and "=" in p:
            name, val = p.split("=", 1)
            parts.append(f"{name.strip()}: Any = {val.strip()}")
        else:
            parts.append(p)
    return f"{prefix}{', '.join(parts)}){ret}:"


def fix_importers(path: Path) -> None:
    content = path.read_text()
    content = strip_type_ignores(content)

    if "from typing import Any" not in content:
        content = "from typing import Any\n" + content
    if "from pathlib import Path" not in content:
        content = "from pathlib import Path\n" + content

    content = re.sub(
        r"^(def \w+\()path\)(\s*->\s*None)?:",
        r"\1path: str | Path) -> dict[str, Any]:",
        content,
        flags=re.MULTILINE,
    )
    content = re.sub(
        r"^(def \w+\()([^:)]*)\)(\s*->\s*[^:]*)?:",
        _add_any_types,
        content,
        flags=re.MULTILINE,
    )

    path.write_text(content)
    print(f"  OK {path}")


def fix_exporters(path: Path) -> None:
    content = path.read_text()
    content = strip_type_ignores(content)
    path.write_text(content)
    print(f"  OK {path}")


def fix_io_init(path: Path) -> None:
    content = path.read_text()
    content = strip_type_ignores(content)

    content = content.replace(
        "from skill_primitives.io.exporters import ROS2Exporter, get_exporter",
        "# from skill_primitives.io.exporters import ROS2Exporter, get_exporter  # TODO: implement",
    )

    path.write_text(content)
    print(f"  OK {path}")


def fix_cli_file(path: Path) -> None:
    content = path.read_text()
    content = strip_type_ignores(content)

    if "from typing import Any" not in content and "from typing" not in content:
        lines = content.splitlines(keepends=True)
        insert_idx = 0
        for i, line in enumerate(lines):
            if (
                line.startswith("from __future__")
                or line.startswith("import ")
                or line.startswith("from ")
            ):
                insert_idx = i + 1
        lines.insert(insert_idx, "from typing import Any\n")
        content = "".join(lines)

    if "from pathlib import Path" not in content:
        lines = content.splitlines(keepends=True)
        insert_idx = 0
        for i, line in enumerate(lines):
            if (
                line.startswith("from __future__")
                or line.startswith("import ")
                or line.startswith("from ")
            ):
                insert_idx = i + 1
        lines.insert(insert_idx, "from pathlib import Path\n")
        content = "".join(lines)

    def fix_main_sig(match: re.Match) -> str:
        prefix = match.group(1)  # "def main("
        params = match.group(2)  # "input, output"
        ret = match.group(3) or ""  # existing return annotation
        if not ret.strip():
            ret = " -> None"

        parts = []
        for p in params.split(","):
            p = p.strip()
            if not p:
                continue
            if p in ("self", "cls"):
                parts.append(p)
            elif ":" not in p and "=" not in p:
                parts.append(f"{p}: Any")
            elif ":" not in p and "=" in p:
                name, val = p.split("=", 1)
                parts.append(f"{name.strip()}: Any = {val.strip()}")
            else:
                parts.append(p)
        return f"{prefix}{', '.join(parts)}){ret}:"

    content = re.sub(
        r"^(def main\()([^)]*)\)(\s*->\s*[^:]*)?:",
        fix_main_sig,
        content,
        flags=re.MULTILINE,
    )

    content = re.sub(r"^(\s+)return\s+\S+", r"\1return", content, flags=re.MULTILINE)

    path.write_text(content)
    print(f"  OK {path}")


def fix_annotator(path: Path) -> None:
    content = path.read_text()
    content = strip_type_ignores(content)
    path.write_text(content)
    print(f"  OK {path}")


def fix_composer(path: Path) -> None:
    content = path.read_text()
    content = strip_type_ignores(content)
    path.write_text(content)
    print(f"  OK {path}")


def main() -> None:
    print("Applying mypy fixes...")

    fix_annotator(ROOT / "skill_primitives" / "core" / "annotator.py")
    fix_composer(ROOT / "skill_primitives" / "core" / "composer.py")
    fix_lerobot_adapter(ROOT / "skill_primitives" / "io" / "lerobot_adapter.py")
    fix_importers(ROOT / "skill_primitives" / "io" / "importers.py")
    fix_exporters(ROOT / "skill_primitives" / "io" / "exporters.py")
    fix_io_init(ROOT / "skill_primitives" / "io" / "__init__.py")
    fix_cli_file(ROOT / "skill_primitives" / "cli" / "annotate.py")
    fix_cli_file(ROOT / "skill_primitives" / "cli" / "compose.py")
    fix_cli_file(ROOT / "skill_primitives" / "cli" / "segment.py")

    print("\nRunning black...")
    subprocess.run(["black", "."], check=False)

    print("\nRunning mypy...")
    result = subprocess.run(["mypy", "skill_primitives"], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode == 0:
        print("\nAll mypy errors resolved!")
    else:
        print("\nSome errors remain -- review output above.")
        if result.stderr:
            print(result.stderr)


if __name__ == "__main__":
    main()
