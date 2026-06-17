# Project Reorganization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the INTRASTAT generator into a Python package with deterministic XLSX/EXE naming and GitHub tag-based EXE releases.

**Architecture:** Keep behavior stable while moving the monolithic script into focused modules under `src/intrastat_generator`. Add small, tested units for version and naming first, then mechanically move existing domain code into package modules and update entry points.

**Tech Stack:** Python 3.11+, Tkinter, openpyxl, optional tkinterdnd2, optional rapidfuzz, pytest, PyInstaller, GitHub Actions.

---

## File Structure

- Create `src/intrastat_generator/__init__.py`: package exports.
- Create `src/intrastat_generator/__main__.py`: `python -m intrastat_generator` entry point.
- Create `src/intrastat_generator/app.py`: console script entry point.
- Create `src/intrastat_generator/cli.py`: command-line parsing and GUI/no-GUI launch.
- Create `src/intrastat_generator/config.py`: constants, defaults, JSON helpers.
- Create `src/intrastat_generator/paths.py`: frozen/source path handling and directory creation.
- Create `src/intrastat_generator/naming.py`: generated XLSX and EXE artifact names.
- Create `src/intrastat_generator/version.py`: version resolution from env/tag/fallback.
- Create `src/intrastat_generator/models.py`: shared dataclasses.
- Create `src/intrastat_generator/text.py`: normalization and numeric helpers.
- Create `src/intrastat_generator/dictionaries.py`: dictionary XML loading.
- Create `src/intrastat_generator/tariff.py`: tariff loading.
- Create `src/intrastat_generator/cn.py`: CN matching.
- Create `src/intrastat_generator/parser.py`: INTRASTAT XML parsing.
- Create `src/intrastat_generator/transport.py`: transport route costs and statistical value calculation.
- Create `src/intrastat_generator/workbook.py`: XLSX generation.
- Create `src/intrastat_generator/service.py`: orchestration service.
- Create `src/intrastat_generator/gui.py`: Tkinter UI.
- Create `tests/test_naming.py`: naming unit tests.
- Create `tests/test_version.py`: version unit tests.
- Create `.github/workflows/release.yml`: tag release workflow.
- Create `.gitignore`, `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`, `README.md`.
- Remove or replace `intrastat_generator_gui_v3_3.py` with a compatibility wrapper.

---

### Task 1: Add Project Metadata And Ignore Rules

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `pyproject.toml`
- Create: `README.md`

- [ ] **Step 1: Create `.gitignore`**

Use these exact entries:

```gitignore
# Runtime files created by the generator
config.json
koszty_transportu.json
logi/
wygenerowane_xlsx/

# Python
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.coverage
htmlcov/

# Virtual environments
.venv/
venv/
env/

# Build artifacts
build/
dist/
*.spec

# Packaging metadata
*.egg-info/

# Editors and OS
.idea/
.vscode/
.DS_Store
Thumbs.db
```

- [ ] **Step 2: Create runtime requirements**

`requirements.txt`:

```text
openpyxl>=3.1.0
rapidfuzz>=3.0.0
tkinterdnd2>=0.3.0
```

- [ ] **Step 3: Create dev requirements**

`requirements-dev.txt`:

```text
-r requirements.txt
pytest>=8.0.0
pyinstaller>=6.0.0
```

- [ ] **Step 4: Create package metadata**

`pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "intrastat-generator"
version = "0.0.0"
description = "Generator XLSX INTRASTAT"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "openpyxl>=3.1.0",
  "rapidfuzz>=3.0.0",
  "tkinterdnd2>=0.3.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0",
  "pyinstaller>=6.0.0",
]

[project.scripts]
intrastat-generator = "intrastat_generator.app:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 5: Create README**

`README.md` should describe local install, CLI help, GUI launch, and release tags:

```markdown
# Generator INTRASTAT XLSX

Desktop/CLI generator plików XLSX do importu INTRASTAT.

## Uruchomienie lokalne

```powershell
python -m pip install -r requirements.txt
python -m intrastat_generator
```

## Tryb CLI

```powershell
python -m intrastat_generator --input intrastat.xml --tariff Taryfa\taryfa.txt --no-gui
```

## Release EXE

Release jest tworzony z tagów `v*`, np. `v3.4.0`.
Artefakt ma nazwę `Intrastat-Generator_<tag>_Windows_x64.exe`.
```

- [ ] **Step 6: Commit metadata**

Run:

```powershell
git add .gitignore requirements.txt requirements-dev.txt pyproject.toml README.md
git commit -m "chore: add project metadata"
```

---

### Task 2: Add Failing Tests For Naming And Versioning

**Files:**
- Create: `tests/test_naming.py`
- Create: `tests/test_version.py`

- [ ] **Step 1: Write naming tests**

`tests/test_naming.py`:

```python
from pathlib import Path

from intrastat_generator.naming import (
    build_release_exe_name,
    build_xlsx_filename,
    make_unique_path,
    safe_filename_part,
)


def test_safe_filename_part_replaces_unsafe_characters():
    assert safe_filename_part("ABC/12:34  test") == "ABC_12_34_test"


def test_build_xlsx_filename_uses_declaration_period_and_timestamp():
    filename = build_xlsx_filename("DEC/123", "2026", "06", "20260617-121314")
    assert filename == "INTRASTAT_DEC_123_2026-06_20260617-121314.xlsx"


def test_build_xlsx_filename_omits_missing_period_parts():
    filename = build_xlsx_filename("", "", "", "20260617-121314")
    assert filename == "INTRASTAT_20260617-121314.xlsx"


def test_make_unique_path_adds_numeric_suffix(tmp_path: Path):
    existing = tmp_path / "INTRASTAT_DEC_2026-06_20260617-121314.xlsx"
    existing.write_text("already exists", encoding="utf-8")

    unique = make_unique_path(existing)

    assert unique.name == "INTRASTAT_DEC_2026-06_20260617-121314_1.xlsx"


def test_build_release_exe_name_keeps_tag_prefix():
    assert build_release_exe_name("v3.4.0") == "Intrastat-Generator_v3.4.0_Windows_x64.exe"
```

- [ ] **Step 2: Write version tests**

`tests/test_version.py`:

```python
from intrastat_generator.version import DEFAULT_VERSION, resolve_version


def test_resolve_version_prefers_explicit_build_env():
    env = {"INTRASTAT_GENERATOR_VERSION": "v3.4.0", "GITHUB_REF_NAME": "v3.3.0"}
    assert resolve_version(env) == "v3.4.0"


def test_resolve_version_uses_github_tag_ref():
    env = {"GITHUB_REF_NAME": "v3.4.0"}
    assert resolve_version(env) == "v3.4.0"


def test_resolve_version_ignores_non_tag_ref():
    env = {"GITHUB_REF_NAME": "dev"}
    assert resolve_version(env) == DEFAULT_VERSION


def test_resolve_version_uses_default_without_env():
    assert resolve_version({}) == DEFAULT_VERSION
```

- [ ] **Step 3: Verify tests fail before implementation**

Run:

```powershell
python -m pytest tests/test_naming.py tests/test_version.py
```

Expected: import failure because `intrastat_generator.naming` and `intrastat_generator.version` do not exist yet.

---

### Task 3: Implement Naming And Version Units

**Files:**
- Create: `src/intrastat_generator/__init__.py`
- Create: `src/intrastat_generator/naming.py`
- Create: `src/intrastat_generator/version.py`

- [ ] **Step 1: Create package marker**

`src/intrastat_generator/__init__.py`:

```python
from .version import DEFAULT_VERSION, get_version, resolve_version

__all__ = ["DEFAULT_VERSION", "get_version", "resolve_version"]
```

- [ ] **Step 2: Implement version unit**

`src/intrastat_generator/version.py`:

```python
from __future__ import annotations

import os
from collections.abc import Mapping

DEFAULT_VERSION = "0.0.0-dev"
VERSION_ENV = "INTRASTAT_GENERATOR_VERSION"


def resolve_version(env: Mapping[str, str] | None = None) -> str:
    values = os.environ if env is None else env
    explicit = values.get(VERSION_ENV, "").strip()
    if explicit:
        return explicit

    github_ref = values.get("GITHUB_REF_NAME", "").strip()
    if github_ref.startswith("v"):
        return github_ref

    return DEFAULT_VERSION


def get_version() -> str:
    return resolve_version()
```

- [ ] **Step 3: Implement naming unit**

`src/intrastat_generator/naming.py`:

```python
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def safe_filename_part(value: object, fallback: str = "") -> str:
    text = "" if value is None else str(value).strip()
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or fallback


def build_xlsx_filename(declaration_no: object, year: object, month: object, timestamp: str | None = None) -> str:
    stamp = timestamp or now_stamp()
    declaration = safe_filename_part(declaration_no, "INTRASTAT")
    year_part = safe_filename_part(year)
    month_part = safe_filename_part(month)

    parts = ["INTRASTAT"]
    if declaration and declaration != "INTRASTAT":
        parts.append(declaration)
    if year_part and month_part:
        parts.append(f"{year_part}-{month_part}")
    elif year_part:
        parts.append(year_part)
    elif month_part:
        parts.append(month_part)
    parts.append(safe_filename_part(stamp, "timestamp"))
    return "_".join(parts) + ".xlsx"


def build_release_exe_name(version: str) -> str:
    return f"Intrastat-Generator_{safe_filename_part(version, '0.0.0-dev')}_Windows_x64.exe"


def make_unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    for index in range(1, 1000):
        candidate = path.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
    return path.with_name(f"{stem}_{now_stamp()}{suffix}")
```

- [ ] **Step 4: Verify tests pass**

Run:

```powershell
python -m pytest tests/test_naming.py tests/test_version.py
```

Expected: all tests pass.

- [ ] **Step 5: Commit naming/version**

Run:

```powershell
git add src/intrastat_generator tests
git commit -m "feat: add naming and version helpers"
```

---

### Task 4: Move Monolith Into Package Modules

**Files:**
- Create/modify package modules under `src/intrastat_generator/`
- Replace: `intrastat_generator_gui_v3_3.py`

- [ ] **Step 1: Mechanically split imports/constants/helpers**

Move existing constants and helper functions into:

- `config.py`: `APP_NAME_BASE`, `CONFIG_FILE`, `OUTPUT_DIR_NAME`, `DICT_DIR_NAME`, `LOG_DIR_NAME`, `ROUTE_COSTS_FILE`, `DEFAULT_CONFIG`, `VOIVODESHIPS`, route cost defaults, workbook style constants that are config-like.
- `paths.py`: `get_app_dir`, `resolve_path`, `ensure_dirs`, `log_exception`.
- `text.py`: `strip_ns`, `norm_text`, `norm_key`, `tokens`, `compact_cn`, `clean_description`, `safe_int`, `safe_float`, `yes_no`, `parse_yes_no`.
- `models.py`: `DictionaryData`, `TariffEntry`, `IntrastatItem`, `StatValueResult`, `CnDecision`.

- [ ] **Step 2: Mechanically split domain classes**

Move existing classes:

- `DictionaryLoader` to `dictionaries.py`.
- `TariffLoader` to `tariff.py`.
- `CnResolver` to `cn.py`.
- `IntrastatXmlParser` to `parser.py`.
- `RouteCostManager` and `StatisticalValueCalculator` to `transport.py`.
- `WorkbookBuilder` and `make_comment` to `workbook.py`.
- `GeneratorService` to `service.py`.
- `App` and Tkinter imports to `gui.py`.
- `main` and argparse handling to `cli.py`.

- [ ] **Step 3: Wire imports explicitly**

Each module imports only the helpers it uses from sibling modules. Avoid wildcard imports.

- [ ] **Step 4: Add entry points**

`src/intrastat_generator/app.py`:

```python
from __future__ import annotations

from .cli import main

__all__ = ["main"]
```

`src/intrastat_generator/__main__.py`:

```python
from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Replace top-level script with wrapper**

`intrastat_generator_gui_v3_3.py`:

```python
#!/usr/bin/env python3
from intrastat_generator.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Run CLI import check**

Run:

```powershell
python -m intrastat_generator --help
```

Expected: argparse help output and exit code 0.

---

### Task 5: Integrate Version And Naming Into Application Flow

**Files:**
- Modify: `src/intrastat_generator/config.py`
- Modify: `src/intrastat_generator/service.py`
- Modify: `src/intrastat_generator/gui.py`
- Modify: `src/intrastat_generator/workbook.py`

- [ ] **Step 1: Use versioned app name**

`config.py` exposes:

```python
APP_NAME_BASE = "Generator INTRASTAT XLSX"


def app_name(version: str) -> str:
    return f"{APP_NAME_BASE} {version}"
```

- [ ] **Step 2: Update GUI**

`gui.py` imports `get_version` and `app_name`, sets:

```python
self.version = get_version()
self.root.title(app_name(self.version))
ttk.Label(frm, text=app_name(self.version), font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 10))
```

- [ ] **Step 3: Update service output naming**

`service.py` imports `build_xlsx_filename` and uses:

```python
filename = build_xlsx_filename(declaration_no, year, month)
xlsx_path = paths["output"] / filename
```

- [ ] **Step 4: Update workbook metadata**

`workbook.py` imports `get_version` and sets creator metadata:

```python
wb.properties.creator = f"Generator INTRASTAT XLSX {get_version()}"
```

- [ ] **Step 5: Run focused tests**

Run:

```powershell
python -m pytest tests/test_naming.py tests/test_version.py
python -m intrastat_generator --help
```

Expected: tests pass and help displays.

- [ ] **Step 6: Commit package reorganization**

Run:

```powershell
git add src intrastat_generator_gui_v3_3.py tests pyproject.toml
git commit -m "refactor: reorganize generator into package"
```

---

### Task 6: Add GitHub Release Workflow

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Create release workflow**

`.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags:
      - "v*"
  workflow_dispatch:

permissions:
  contents: write
  actions: read

jobs:
  check-self-hosted:
    name: Check self-hosted runner availability
    runs-on: ubuntu-latest
    outputs:
      available: ${{ steps.check.outputs.available }}
    steps:
      - name: Check repository runners
        id: check
        env:
          GH_TOKEN: ${{ github.token }}
          REPOSITORY: ${{ github.repository }}
        shell: pwsh
        run: |
          $response = gh api "repos/$env:REPOSITORY/actions/runners?per_page=100" | ConvertFrom-Json
          $available = $false
          foreach ($runner in $response.runners) {
            $labels = @($runner.labels | ForEach-Object { $_.name })
            $hasLabels = $labels -contains "self-hosted" -and $labels -contains "Windows" -and $labels -contains "X64"
            if ($runner.status -eq "online" -and -not $runner.busy -and $hasLabels) {
              $available = $true
              break
            }
          }
          "available=$($available.ToString().ToLowerInvariant())" >> $env:GITHUB_OUTPUT

  build-self-hosted:
    name: Build on self-hosted Windows runner
    needs: check-self-hosted
    if: needs.check-self-hosted.outputs.available == 'true'
    runs-on: [self-hosted, Windows, X64]
    timeout-minutes: 30
    env:
      INTRASTAT_GENERATOR_VERSION: ${{ github.ref_name }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install -r requirements-dev.txt
          python -m pip install -e .
      - name: Run tests
        run: python -m pytest
      - name: Build EXE
        run: |
          python -m PyInstaller --onefile --windowed --name intrastat-generator --paths src src/intrastat_generator/__main__.py
          python -c "from pathlib import Path; from intrastat_generator.naming import build_release_exe_name; Path('dist/intrastat-generator.exe').rename(Path('dist') / build_release_exe_name('${{ github.ref_name }}'))"
      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: intrastat-generator-windows-x64
          path: dist/Intrastat-Generator_*_Windows_x64.exe

  build-github-hosted:
    name: Build on GitHub-hosted Windows runner
    needs: [check-self-hosted, build-self-hosted]
    if: always() && (needs.check-self-hosted.outputs.available != 'true' || needs.build-self-hosted.result == 'failure' || needs.build-self-hosted.result == 'cancelled')
    runs-on: windows-latest
    timeout-minutes: 30
    env:
      INTRASTAT_GENERATOR_VERSION: ${{ github.ref_name }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install -r requirements-dev.txt
          python -m pip install -e .
      - name: Run tests
        run: python -m pytest
      - name: Build EXE
        run: |
          python -m PyInstaller --onefile --windowed --name intrastat-generator --paths src src/intrastat_generator/__main__.py
          python -c "from pathlib import Path; from intrastat_generator.naming import build_release_exe_name; Path('dist/intrastat-generator.exe').rename(Path('dist') / build_release_exe_name('${{ github.ref_name }}'))"
      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: intrastat-generator-windows-x64
          path: dist/Intrastat-Generator_*_Windows_x64.exe

  publish-release:
    name: Publish GitHub Release
    needs: [build-self-hosted, build-github-hosted]
    if: always() && (needs.build-self-hosted.result == 'success' || needs.build-github-hosted.result == 'success')
    runs-on: ubuntu-latest
    steps:
      - name: Download artifact
        uses: actions/download-artifact@v4
        with:
          name: intrastat-generator-windows-x64
          path: release-artifacts
      - name: Publish release
        uses: softprops/action-gh-release@v2
        with:
          files: release-artifacts/Intrastat-Generator_*_Windows_x64.exe
          generate_release_notes: true
```

- [ ] **Step 2: Commit workflow**

Run:

```powershell
git add .github/workflows/release.yml
git commit -m "ci: add tag based release workflow"
```

---

### Task 7: Final Verification

**Files:**
- All changed files.

- [ ] **Step 1: Run full tests**

Run:

```powershell
python -m pytest
```

Expected: all tests pass.

- [ ] **Step 2: Run CLI help**

Run:

```powershell
python -m intrastat_generator --help
```

Expected: help text displays and includes `--no-gui`, `--input`, and `--tariff`.

- [ ] **Step 3: Check git status**

Run:

```powershell
git status --short
```

Expected: clean working tree after commits.

- [ ] **Step 4: Report result**

Summarize:

- Package layout created.
- Naming/version tests added.
- GUI/header version mismatch fixed.
- Release workflow added with self-hosted-first behavior and GitHub fallback.
- Runtime/build outputs ignored.
