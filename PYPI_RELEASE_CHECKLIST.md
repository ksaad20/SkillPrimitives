# PyPI Release Checklist

> **For:** `skill-primitives` — Natural Language to Robot Motion  
> **Target:** `v0.1.0` or higher (do not release `v0.0.x` on PyPI)

---

## 1. Package Fundamentals

- [ ] **Version is semantic** — `0.1.0` or higher. `0.0.x` signals "not ready for users."
- [ ] **`pyproject.toml` is complete**
  - `name` is unique on PyPI (check `pip install <name>` and [pypi.org/search](https://pypi.org/search))
  - `description` ≤ 100 chars (appears in search results)
  - `readme` renders correctly on PyPI (test with `python -m build && twine check dist/*`)
  - `license` has an SPDX identifier (`Apache-2.0`, `MIT`, etc.)
  - `requires-python` matches your CI matrix (e.g. `>=3.9`)
  - `classifiers` are accurate (remove `3 - Alpha` if you're claiming usability)
  - `keywords` are present (affects PyPI search ranking)
- [ ] **Entry points work** — `sp-segment`, `sp-annotate`, `sp-compose`, `sp-demo` are registered and tested
- [ ] **Package structure is clean** — `import skill_primitives` works from a fresh virtualenv
- [ ] **No top-level namespace pollution** — `pip install` doesn't dump files into `site-packages/` root

---

## 2. Build & Distribution

- [ ] **`python -m build` produces clean artifacts**
  - `dist/*.whl` (universal or platform-specific)
  - `dist/*.tar.gz` (sdist)
- [ ] **`twine check dist/*` passes** with zero warnings
- [ ] **Wheel is not empty** — `unzip -l dist/*.whl` shows your Python files inside
- [ ] **No accidental file inclusion** — `.pyc`, `__pycache__`, `.git`, `tests/`, `zoo/` are excluded
- [ ] **TestPyPI dry-run succeeds**

  ```bash
  python -m build
  python -m twine upload --repository testpypi dist/*
  pip install --index-url https://test.pypi.org/simple/ --no-deps skill-primitives==<version>
  ```

- [ ] **Install from TestPyPI works in a clean virtualenv**
  - `python -c "import skill_primitives; print(skill_primitives.__version__)"` succeeds
  - CLI entry points (`sp-segment --help`) execute without import errors

---

## 3. Quality Gates (All Green)

- [ ] **`pytest` passes** — 100% collection success, zero import errors
- [ ] **Coverage is honest** — `fail_under` in `pyproject.toml` matches reality (don't claim 80% at 48%)
- [ ] **`black --check .` passes**
- [ ] **`ruff check .` passes**
- [ ] **`mypy` passes** on the installed package (not just the source tree)
- [ ] **No uncommitted changes** — `git status` is clean on the release commit
- [ ] **Git tag exists** — `git tag -a v0.1.0 -m "Release v0.1.0"` pushed to origin

---

## 4. Documentation & Discoverability

- [ ] **README has a "Quickstart" section** — copy-paste 3 commands, see output
- [ ] **README documents installation** — `pip install skill-primitives[dev]` or `[all]`
- [ ] **CHANGELOG.md has an entry** for this version with user-facing changes
- [ ] **LICENSE file is present** in the repo and included in the sdist
- [ ] **CITATION.cff is present** (critical for research software — academics need to cite you)
- [ ] **GitHub repo has a description and topics** (affects PyPI's "Project links" SEO)

---

## 5. Release Mechanics

- [ ] **GitHub Actions workflow for PyPI publishing** using [trusted publishing](https://docs.pypi.org/trusted-publishers/) (OIDC, no API tokens in secrets)
- [ ] **Release triggered by GitHub Release** (not manual `twine upload` from laptop)
- [ ] **Version bump is automated** — `hatchling version patch` or `bump2version`, not hand-edited
- [ ] **Yank policy is documented** — "If we break the API in `0.2.0`, we will yank `0.1.0`"

---

## 6. Post-Release (Within 24 Hours)

- [ ] **PyPI page renders correctly** — description, classifiers, project links all visible
- [ ] **`pip install skill-primitives` works** from a fresh virtualenv on Linux, macOS, Windows
- [ ] **CLI tools are in `$PATH`** — `which sp-segment` returns a path
- [ ] **GitHub Release notes are published** with assets (source tarball + wheel)
- [ ] **Hugging Face dataset is live** (for your project specifically — the real value is the data, not the pip package)
- [ ] **Monitor for 48 hours** — watch PyPI download stats and GitHub issues for `ModuleNotFoundError`

---

## 7. SkillPrimitives-Specific Additions

| Item | Why it matters for robotics |
|------|----------------------------|
| `lerobot` extra installs cleanly | Your core dependency — `pip install skill-primitives[lerobot]` must resolve |
| `zoo/` is **not** in the wheel | Generated artifacts bloat the package; build them locally or in CI |
| `tests/` is **not** in the wheel | `pip install` shouldn't ship your test suite |
| `sp-demo` has a `--dry-run` flag | Users won't have a robot connected; they need to see what it *would* do |
| README shows `from skill_primitives import get_primitive` | The registry is your API surface — make it the hero example |

---

## Recommended Release Timeline

| Milestone | Version | PyPI? |
|-----------|---------|-------|
| Green CI + 5 primitives | `0.0.1` | ❌ No — use `pip install git+https://...` |
| 10+ primitives + HF dataset | `0.1.0` | ⚠️ TestPyPI only |
| End-to-end `annotate → compose → demo` works | `0.2.0` | ✅ Yes — this is your first real release |
| Paper submission / blog post | `0.3.0` | ✅ Yes — timing the release with visibility |

> **Rule of thumb:** Don't waste the `0.1.0` announcement on a build system. Save it for when someone can `pip install` your package and segment a LeRobot trajectory in 5 minutes.
