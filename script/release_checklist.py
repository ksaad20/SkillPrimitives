#!/usr/bin/env python3
"""
release_checklist.py — Pre-release validation suite.

Runs a comprehensive set of checks before any release to ensure:
  • All primitives build cleanly
  • Metadata is complete and valid
  • Tests pass
  • Version numbers are consistent
  • CHANGELOG is updated
  • No secrets or debug code committed
  • Git status is clean (or explicitly dirty)

Usage:
    ./scripts/release_checklist.py              # Full validation
    ./scripts/release_checklist.py --fix        # Auto-fix where possible
    ./scripts/release_checklist.py --version 1.2.3  # Verify against version
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()

# ── Configuration ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRIMITIVES_DIR = PROJECT_ROOT / "primitives"
ZOO_DIR = PROJECT_ROOT / "zoo"
TESTS_DIR = PROJECT_ROOT / "tests"
CHANGELOG = PROJECT_ROOT / "CHANGELOG.md"
PYPROJECT = PROJECT_ROOT / "pyproject.toml"
PACKAGE_JSON = PROJECT_ROOT / "package.json"
MANIFEST = PROJECT_ROOT / "zoo_manifest.json"

SECRETS_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
    (r"sk-[a-zA-Z0-9]{48}", "OpenAI API Key"),
    (r"private_key[\s]*=[\s]*['\"][^'\"]{20,}", "Private Key"),
    (r"password[\s]*=[\s]*['\"][^'\"]+['\"]", "Hardcoded Password"),
    (r"api_key[\s]*=[\s]*['\"][^'\"]{10,}", "Hardcoded API Key"),
]

DEBUG_PATTERNS = [
    (r"console\.log\(", "JavaScript console.log"),
    (r'print\(["\']DEBUG', "Python debug print"),
    (r"debugger;", "JavaScript debugger"),
    (r"TODO\s*[:\-]?\s*fixme", "TODO/FIXME marker"),
    (r"XXX", "XXX marker"),
]


class CheckResult:
    def __init__(self, name: str, passed: bool, message: str = "", fixable: bool = False):
        self.name = name
        self.passed = passed
        self.message = message
        self.fixable = fixable


class ReleaseChecklist:
    def __init__(self, project_root: Path, target_version: Optional[str] = None):
        self.project_root = project_root
        self.target_version = target_version
        self.results: list[CheckResult] = []
        self.fix_mode = False

    # ── Individual Checks ──────────────────────────────────────────────────────
    def check_git_clean(self) -> CheckResult:
        """Verify git working tree is clean (or changes are expected)."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            if result.stdout.strip():
                lines = result.stdout.strip().split("\n")
                return CheckResult(
                    "Git Working Tree Clean",
                    False,
                    f"{len(lines)} uncommitted change(s). Run 'git status' for details.",
                )
            return CheckResult("Git Working Tree Clean", True, "Working tree is clean")
        except subprocess.CalledProcessError as e:
            return CheckResult("Git Working Tree Clean", False, f"Git error: {e}")

    def check_changelog_updated(self) -> CheckResult:
        """Verify CHANGELOG.md has an entry for the target version."""
        if not CHANGELOG.exists():
            return CheckResult("CHANGELOG Updated", False, f"{CHANGELOG} not found")

        content = CHANGELOG.read_text(encoding="utf-8")

        if self.target_version:
            pattern = re.compile(
                rf"^##\s*\[?{re.escape(self.target_version)}\]?",
                re.MULTILINE,
            )
            if not pattern.search(content):
                return CheckResult(
                    "CHANGELOG Updated",
                    False,
                    f"No entry for version {self.target_version} in CHANGELOG.md",
                    fixable=True,
                )
            return CheckResult("CHANGELOG Updated", True, f"Found entry for {self.target_version}")

        # If no target version, just check it has recent content
        if "## " not in content:
            return CheckResult("CHANGELOG Updated", False, "CHANGELOG appears empty")
        return CheckResult("CHANGELOG Updated", True, "CHANGELOG has entries")

    def check_version_consistency(self) -> CheckResult:
        """Ensure version numbers match across files."""
        versions = {}

        if PYPROJECT.exists():
            content = PYPROJECT.read_text(encoding="utf-8")
            m = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            if m:
                versions["pyproject.toml"] = m.group(1)

        if PACKAGE_JSON.exists():
            with open(PACKAGE_JSON, encoding="utf-8") as f:
                data = json.load(f)
                versions["package.json"] = data.get("version", "N/A")

        if MANIFEST.exists():
            with open(MANIFEST, encoding="utf-8") as f:
                data = json.load(f)
                # Manifest doesn't typically store top-level version
                pass

        if not versions:
            return CheckResult("Version Consistency", True, "No version files found")

        unique = set(versions.values())
        if len(unique) > 1:
            details = ", ".join(f"{k}={v}" for k, v in versions.items())
            return CheckResult(
                "Version Consistency",
                False,
                f"Version mismatch: {details}",
                fixable=True,
            )

        detected = list(unique)[0]
        if self.target_version and detected != self.target_version:
            return CheckResult(
                "Version Consistency",
                False,
                f"Detected {detected}, expected {self.target_version}",
                fixable=True,
            )

        return CheckResult("Version Consistency", True, f"All files at version {detected}")

    def check_tests_pass(self) -> CheckResult:
        """Run test suite and verify all tests pass."""
        if not TESTS_DIR.exists():
            return CheckResult("Tests Pass", True, "No tests directory found — skipped")

        # Try pytest first, then unittest
        for cmd, name in [
            (["pytest", "-q"], "pytest"),
            (["python", "-m", "pytest", "-q"], "python -m pytest"),
        ]:
            if shutil.which(cmd[0]):
                result = subprocess.run(
                    cmd,
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    return CheckResult("Tests Pass", True, f"All tests passed via {name}")
                else:
                    # Extract failure count
                    fail_match = re.search(r"(\d+) failed", result.stdout + result.stderr)
                    fails = fail_match.group(1) if fail_match else "some"
                    return CheckResult(
                        "Tests Pass",
                        False,
                        f"{fails} test(s) failed. Run '{name}' for details.",
                    )

        return CheckResult("Tests Pass", False, "No test runner found (pytest required)")

    def check_no_secrets(self) -> CheckResult:
        """Scan for accidentally committed secrets."""
        findings = []
        scan_dirs = [PRIMITIVES_DIR, ZOO_DIR, PROJECT_ROOT / "src"]

        for scan_dir in scan_dirs:
            if not scan_dir.exists():
                continue
            for file_path in scan_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                if file_path.suffix not in {
                    ".js",
                    ".ts",
                    ".py",
                    ".yaml",
                    ".yml",
                    ".json",
                    ".html",
                    ".css",
                    ".sh",
                }:
                    continue

                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue

                for pattern, desc in SECRETS_PATTERNS:
                    if re.search(pattern, content):
                        rel = file_path.relative_to(self.project_root)
                        findings.append(f"{rel}: possible {desc}")

        if findings:
            return CheckResult(
                "No Secrets Leaked",
                False,
                f"Found {len(findings)} potential secret(s):\n  " + "\n  ".join(findings[:5]),
            )
        return CheckResult("No Secrets Leaked", True, "No secrets detected")

    def check_no_debug_code(self) -> CheckResult:
        """Scan for leftover debug statements."""
        findings = []
        scan_dirs = [PRIMITIVES_DIR, ZOO_DIR, PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"]

        for scan_dir in scan_dirs:
            if not scan_dir.exists():
                continue
            for file_path in scan_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                if file_path.suffix not in {".js", ".ts", ".py", ".html"}:
                    continue

                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue

                for pattern, desc in DEBUG_PATTERNS:
                    for line_num, line in enumerate(content.splitlines(), 1):
                        if re.search(pattern, line):
                            rel = file_path.relative_to(self.project_root)
                            findings.append(f"{rel}:{line_num}: {desc}")

        if findings:
            return CheckResult(
                "No Debug Code",
                False,
                f"Found {len(findings)} debug marker(s):\n  " + "\n  ".join(findings[:5]),
            )
        return CheckResult("No Debug Code", True, "No debug code detected")

    def check_primitives_valid(self) -> CheckResult:
        """Validate all primitive specs are parseable and complete."""
        if not PRIMITIVES_DIR.exists():
            return CheckResult("Primitives Valid", True, "No primitives directory")

        errors = []
        required = {"name", "version", "category", "description", "author"}

        for primitive_dir in sorted(PRIMITIVES_DIR.iterdir()):
            if not primitive_dir.is_dir() or primitive_dir.name.startswith((".", "_")):
                continue

            spec_path = primitive_dir / "spec.yaml"
            if not spec_path.exists():
                errors.append(f"{primitive_dir.name}: Missing spec.yaml")
                continue

            try:
                with open(spec_path, encoding="utf-8") as f:
                    spec = yaml.safe_load(f)
            except yaml.YAMLError as e:
                errors.append(f"{primitive_dir.name}: Invalid YAML — {e}")
                continue

            missing = required - set(spec.keys())
            if missing:
                errors.append(f"{primitive_dir.name}: Missing fields {missing}")

        if errors:
            return CheckResult(
                "Primitives Valid",
                False,
                f"{len(errors)} primitive(s) invalid:\n  " + "\n  ".join(errors[:5]),
            )
        return CheckResult("Primitives Valid", True, "All primitives valid")

    def check_manifest_fresh(self) -> CheckResult:
        """Ensure zoo manifest exists and is newer than source files."""
        if not MANIFEST.exists():
            return CheckResult(
                "Manifest Fresh",
                False,
                "zoo_manifest.json not found. Run build_zoo.py first.",
            )

        manifest_mtime = MANIFEST.stat().st_mtime
        if PRIMITIVES_DIR.exists():
            for f in PRIMITIVES_DIR.rglob("*"):
                if f.is_file() and f.stat().st_mtime > manifest_mtime:
                    return CheckResult(
                        "Manifest Fresh",
                        False,
                        f"{f.relative_to(self.project_root)} is newer than manifest. Rebuild needed.",
                        fixable=True,
                    )
        return CheckResult("Manifest Fresh", True, "Manifest is up to date")

    def check_builds_cleanly(self) -> CheckResult:
        """Run build_zoo.py and verify it exits cleanly."""
        build_script = PROJECT_ROOT / "scripts" / "build_zoo.py"
        if not build_script.exists():
            return CheckResult("Builds Cleanly", True, "No build script found — skipped")

        result = subprocess.run(
            [sys.executable, str(build_script)],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return CheckResult(
                "Builds Cleanly",
                False,
                "build_zoo.py failed. Run it manually for details.",
                fixable=True,
            )
        return CheckResult("Builds Cleanly", True, "Zoo builds without errors")

    # ── Auto-fix ───────────────────────────────────────────────────────────────
    def auto_fix(self):
        """Attempt to automatically fix fixable issues."""
        console.print("\n[bold cyan]🔧 Attempting auto-fixes...[/bold cyan]\n")
        fixed = 0

        for result in self.results:
            if result.passed or not result.fixable:
                continue

            if result.name == "Manifest Fresh":
                build_script = PROJECT_ROOT / "scripts" / "build_zoo.py"
                if build_script.exists():
                    console.print(f"  Running build_zoo.py for '{result.name}'...")
                    subprocess.run([sys.executable, str(build_script)], cwd=self.project_root)
                    fixed += 1

            elif result.name == "CHANGELOG Updated" and self.target_version:
                # Add a template entry
                if CHANGELOG.exists():
                    content = CHANGELOG.read_text(encoding="utf-8")
                    today = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
                    new_entry = f"\n## [{self.target_version}] — {today}\n\n- Release version {self.target_version}\n"
                    # Insert after header
                    lines = content.splitlines()
                    insert_idx = 0
                    for i, line in enumerate(lines):
                        if line.startswith("# ") and i > 0:
                            insert_idx = i + 1
                            break
                    lines.insert(insert_idx, new_entry)
                    CHANGELOG.write_text("\n".join(lines), encoding="utf-8")
                    console.print(f"  Added CHANGELOG entry for {self.target_version}")
                    fixed += 1

        if fixed:
            console.print(f"\n[green]Applied {fixed} fix(es). Re-running checks...[/green]\n")
            self.results = []
            self.run_all()
        else:
            console.print("[yellow]No applicable fixes found.[/yellow]")

    # ── Orchestration ──────────────────────────────────────────────────────────
    def run_all(self):
        """Execute all checks."""
        checks = [
            self.check_git_clean,
            self.check_version_consistency,
            self.check_changelog_updated,
            self.check_primitives_valid,
            self.check_manifest_fresh,
            self.check_builds_cleanly,
            self.check_tests_pass,
            self.check_no_secrets,
            self.check_no_debug_code,
        ]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            for check_fn in checks:
                progress.update(progress.add_task(f"Running {check_fn.__name__}..."), total=1)
                self.results.append(check_fn())

    def report(self) -> bool:
        """Display results and return overall pass/fail."""
        console.rule("[bold green]📋 Release Checklist Results[/bold green]")

        table = Table(show_header=True, header_style="bold")
        table.add_column("Check", style="cyan", min_width=25)
        table.add_column("Status", justify="center", width=10)
        table.add_column("Details", style="dim")

        all_passed = True
        for result in self.results:
            status = "[green]✓ PASS[/green]" if result.passed else "[red]✗ FAIL[/red]"
            if not result.passed:
                all_passed = False
            table.add_row(result.name, status, result.message)

        console.print(table)

        # Summary panel
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)

        if all_passed:
            console.print(
                Panel(
                    f"[bold green]All {total} checks passed![/bold green]\n"
                    "This release is ready to ship. 🚀",
                    title="Release Ready",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    f"[bold red]{total - passed} of {total} checks failed.[/bold red]\n"
                    "Address the failures above before releasing.",
                    title="Release Blocked",
                    border_style="red",
                )
            )

        return all_passed


def main():
    parser = argparse.ArgumentParser(description="Pre-release validation checklist")
    parser.add_argument("--version", help="Target release version to validate against")
    parser.add_argument("--fix", action="store_true", help="Auto-fix issues where possible")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    args = parser.parse_args()

    checklist = ReleaseChecklist(PROJECT_ROOT, target_version=args.version)
    checklist.fix_mode = args.fix

    checklist.run_all()

    if args.fix:
        checklist.auto_fix()

    passed = checklist.report()
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
