# Icons Repository Updates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add application/GitHub icons, repository information, and public GitHub release update detection/download to the Tkinter app.

**Architecture:** Keep non-GUI behavior in small modules: `project.py` for metadata, `assets.py` for icon path resolution, and `updater.py` for public GitHub API/version/download logic. `gui.py` only loads images, displays state, opens links, and runs update operations on worker threads.

**Tech Stack:** Python 3.11, Tkinter/ttk, urllib from the standard library, pytest, PyInstaller, GitHub Releases API.

---

## File Structure

- Create `src/intrastat_generator/project.py`: stable project metadata and repository constants.
- Create `src/intrastat_generator/assets.py`: resolve `Icon/icon.png`, `Icon/github.png`, and `Icon/icon.ico` from source, external app folder, or PyInstaller bundle.
- Create `src/intrastat_generator/updater.py`: version parsing/comparison, GitHub API response parsing, release asset selection, and EXE download.
- Modify `src/intrastat_generator/gui.py`: header icons, GitHub click behavior, project info dialog, background update check, pulsating update button, and download progress.
- Modify `.github/workflows/release.yml`: stage `Icon` assets and pass `--icon` to PyInstaller when `Icon/icon.ico` exists.
- Create `tests/test_project_metadata.py` additions or new tests for project metadata.
- Create `tests/test_assets.py`: asset lookup behavior.
- Create `tests/test_updater.py`: updater behavior.
- Modify `tests/test_release_workflow.py`: icon staging and `--icon` assertions.
- Add generated asset files `Icon/github.png` and `Icon/icon.ico`.

---

### Task 1: Project Metadata

**Files:**
- Create: `src/intrastat_generator/project.py`
- Modify: `tests/test_project_metadata.py`

- [ ] **Step 1: Write the failing metadata test**

```python
def test_project_metadata_contains_repository_information():
    from intrastat_generator.project import PROJECT

    assert PROJECT.name == "intrastat-generator"
    assert PROJECT.display_name == "Generator INTRASTAT XLSX"
    assert PROJECT.repository_owner == "NefilimPL"
    assert PROJECT.repository_name == "intrastat-generator"
    assert PROJECT.repository_url == "https://github.com/NefilimPL/intrastat-generator"
    assert PROJECT.description == "Generator XLSX INTRASTAT"
    assert PROJECT.authors == "NefilimPL and contributors"
    assert PROJECT.license == "MIT"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_project_metadata.py::test_project_metadata_contains_repository_information -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'intrastat_generator.project'`.

- [ ] **Step 3: Implement metadata module**

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectMetadata:
    name: str
    display_name: str
    description: str
    authors: str
    license: str
    repository_owner: str
    repository_name: str

    @property
    def repository_slug(self) -> str:
        return f"{self.repository_owner}/{self.repository_name}"

    @property
    def repository_url(self) -> str:
        return f"https://github.com/{self.repository_slug}"


PROJECT = ProjectMetadata(
    name="intrastat-generator",
    display_name="Generator INTRASTAT XLSX",
    description="Generator XLSX INTRASTAT",
    authors="NefilimPL and contributors",
    license="MIT",
    repository_owner="NefilimPL",
    repository_name="intrastat-generator",
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_project_metadata.py::test_project_metadata_contains_repository_information -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_project_metadata.py src/intrastat_generator/project.py
git commit -m "Add project repository metadata"
```

---

### Task 2: Asset Resolution And Icon Files

**Files:**
- Create: `src/intrastat_generator/assets.py`
- Create: `tests/test_assets.py`
- Create: `Icon/github.png`
- Create: `Icon/icon.ico`

- [ ] **Step 1: Generate icon files**

Use `Icon/icon.png` as input and create `Icon/icon.ico`. Create `Icon/github.png`
as a 64x64 transparent PNG with a dark GitHub-style mark or `GH` glyph. Do not
overwrite `Icon/icon.png`.

- [ ] **Step 2: Write failing asset tests**

```python
from pathlib import Path

from intrastat_generator.assets import AppAssets


def test_assets_find_source_icon_files(tmp_path: Path):
    icon_dir = tmp_path / "Icon"
    icon_dir.mkdir()
    app_icon = icon_dir / "icon.png"
    github_icon = icon_dir / "github.png"
    app_ico = icon_dir / "icon.ico"
    app_icon.write_bytes(b"png")
    github_icon.write_bytes(b"png")
    app_ico.write_bytes(b"ico")

    assets = AppAssets(tmp_path)

    assert assets.app_icon_png == app_icon
    assert assets.github_icon_png == github_icon
    assert assets.app_icon_ico == app_ico


def test_assets_return_none_when_icon_file_is_missing(tmp_path: Path):
    assets = AppAssets(tmp_path)

    assert assets.app_icon_png is None
    assert assets.github_icon_png is None
    assert assets.app_icon_ico is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_assets.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'intrastat_generator.assets'`.

- [ ] **Step 4: Implement asset resolver**

```python
from __future__ import annotations

import sys
from pathlib import Path


class AppAssets:
    def __init__(self, app_dir: Path):
        self.app_dir = Path(app_dir)

    @property
    def app_icon_png(self) -> Path | None:
        return self._first_existing("Icon/icon.png")

    @property
    def github_icon_png(self) -> Path | None:
        return self._first_existing("Icon/github.png")

    @property
    def app_icon_ico(self) -> Path | None:
        return self._first_existing("Icon/icon.ico")

    def _first_existing(self, relative: str) -> Path | None:
        for root in self._roots():
            candidate = root / relative
            if candidate.is_file():
                return candidate
        return None

    def _roots(self) -> list[Path]:
        roots = [self.app_dir]
        bundle_dir = getattr(sys, "_MEIPASS", "")
        if bundle_dir:
            roots.append(Path(bundle_dir))
        return roots
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_assets.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add Icon/github.png Icon/icon.ico tests/test_assets.py src/intrastat_generator/assets.py
git commit -m "Add application asset resolution"
```

---

### Task 3: Updater Version And Release Logic

**Files:**
- Create: `src/intrastat_generator/updater.py`
- Create: `tests/test_updater.py`

- [ ] **Step 1: Write failing version and asset tests**

```python
from intrastat_generator.updater import (
    GitHubAsset,
    is_newer_version,
    parse_version_tuple,
    select_windows_exe_asset,
)


def test_parse_version_tuple_ignores_prefix_and_branch_suffix():
    assert parse_version_tuple("v0.0.6-Main") == (0, 0, 6)
    assert parse_version_tuple("0.0.5-dev") == (0, 0, 5)


def test_parse_version_tuple_returns_none_for_uncomparable_text():
    assert parse_version_tuple("feature-build") is None


def test_is_newer_version_detects_newer_release():
    assert is_newer_version("v0.0.5-dev", "v0.0.6") is True
    assert is_newer_version("v0.0.6-Main", "v0.0.6") is False
    assert is_newer_version("feature-build", "v0.0.1") is False


def test_select_windows_exe_asset_prefers_release_exe():
    asset = select_windows_exe_asset(
        [
            GitHubAsset("notes.txt", "https://example.test/notes", 10),
            GitHubAsset("Intrastat-Generator_v0.0.6_Windows_x64.exe", "https://example.test/app.exe", 20),
        ]
    )

    assert asset is not None
    assert asset.name == "Intrastat-Generator_v0.0.6_Windows_x64.exe"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_updater.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'intrastat_generator.updater'`.

- [ ] **Step 3: Implement version and asset logic**

```python
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class GitHubAsset:
    name: str
    download_url: str
    size: int


def parse_version_tuple(value: str) -> tuple[int, ...] | None:
    match = re.search(r"v?(\d+(?:\.\d+){1,3})", str(value or ""))
    if not match:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def is_newer_version(current: str, latest: str) -> bool:
    current_tuple = parse_version_tuple(current)
    latest_tuple = parse_version_tuple(latest)
    if current_tuple is None or latest_tuple is None:
        return False
    width = max(len(current_tuple), len(latest_tuple))
    return latest_tuple + (0,) * (width - len(latest_tuple)) > current_tuple + (0,) * (width - len(current_tuple))


def select_windows_exe_asset(assets: list[GitHubAsset]) -> GitHubAsset | None:
    for asset in assets:
        lower_name = asset.name.lower()
        if lower_name.endswith(".exe") and "windows" in lower_name:
            return asset
    for asset in assets:
        if asset.name.lower().endswith(".exe"):
            return asset
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_updater.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_updater.py src/intrastat_generator/updater.py
git commit -m "Add updater version checks"
```

---

### Task 4: GitHub Public API And Download Logic

**Files:**
- Modify: `src/intrastat_generator/updater.py`
- Modify: `tests/test_updater.py`

- [ ] **Step 1: Write failing API and download tests**

Add tests that inject fake opener functions:

```python
import json
from pathlib import Path
import urllib.error

from intrastat_generator.project import PROJECT
from intrastat_generator.updater import GitHubReleaseClient, RepositoryVisibility, UpdateStatus


class FakeResponse:
    def __init__(self, payload: bytes, headers: dict[str, str] | None = None):
        self.payload = payload
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, _size: int = -1) -> bytes:
        return self.payload


def test_repository_404_is_private_or_unavailable():
    def opener(_request, timeout=0):
        raise urllib.error.HTTPError("https://api.github.test", 404, "Not Found", {}, None)

    client = GitHubReleaseClient(PROJECT, opener=opener)

    assert client.fetch_repository_visibility() == RepositoryVisibility.PRIVATE_OR_UNAVAILABLE


def test_latest_update_detects_newer_public_release():
    payloads = [
        {"private": False},
        {
            "tag_name": "v0.0.6",
            "html_url": "https://github.com/NefilimPL/intrastat-generator/releases/tag/v0.0.6",
            "assets": [
                {
                    "name": "Intrastat-Generator_v0.0.6_Windows_x64.exe",
                    "browser_download_url": "https://example.test/app.exe",
                    "size": 123,
                }
            ],
        },
    ]

    def opener(_request, timeout=0):
        return FakeResponse(json.dumps(payloads.pop(0)).encode("utf-8"))

    client = GitHubReleaseClient(PROJECT, opener=opener)

    result = client.check_for_update("v0.0.5-dev")

    assert result.status == UpdateStatus.UPDATE_AVAILABLE
    assert result.latest_version == "v0.0.6"
    assert result.asset is not None
    assert result.asset.size == 123


def test_download_asset_writes_unique_exe(tmp_path: Path):
    calls = []

    def opener(_request, timeout=0):
        calls.append(timeout)
        return FakeResponse(b"exe-data", {"Content-Length": "8"})

    client = GitHubReleaseClient(PROJECT, opener=opener)
    asset = client.asset_from_json(
        {
            "name": "Intrastat-Generator_v0.0.6_Windows_x64.exe",
            "browser_download_url": "https://example.test/app.exe",
            "size": 8,
        }
    )

    target = client.download_asset(asset, tmp_path)

    assert target.name == "Intrastat-Generator_v0.0.6_Windows_x64.exe"
    assert target.read_bytes() == b"exe-data"
    assert not (tmp_path / f"{target.name}.part").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_updater.py -v`

Expected: FAIL because `GitHubReleaseClient`, `RepositoryVisibility`, and `UpdateStatus` are missing.

- [ ] **Step 3: Implement API and download logic**

Implement enums/dataclasses for repository visibility and update result, public
API calls through an injectable opener, JSON parsing, and `.part` download
renaming. Use `urllib.request.Request`, `urllib.request.urlopen`, `json.loads`,
and `make_unique_path()`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_updater.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_updater.py src/intrastat_generator/updater.py
git commit -m "Add GitHub release update client"
```

---

### Task 5: GUI Header, Repo Info, And Update Threads

**Files:**
- Modify: `src/intrastat_generator/gui.py`

- [ ] **Step 1: Keep GUI behavior behind already-tested helpers**

Use only helpers already covered by `tests/test_assets.py` and
`tests/test_updater.py` for non-rendering behavior. Do not add display-dependent
Tkinter tests because CI may not provide a display.

- [ ] **Step 2: Modify GUI imports and state**

Add imports for `webbrowser`, `AppAssets`, `PROJECT`, `GitHubReleaseClient`,
`RepositoryVisibility`, `UpdateResult`, and `UpdateStatus`. Store `self.assets`,
`self.github_client`, `self.repository_visibility`, `self.latest_update`, and
`self.downloaded_update_path`.

- [ ] **Step 3: Replace title label with header frame**

Create a header frame with application icon image, application title label,
GitHub icon button, info button, and hidden update button. Keep references to
`PhotoImage` objects on `self` so Tkinter does not garbage collect them.

- [ ] **Step 4: Add repository click and info handlers**

Add `_github_clicked()` to open `PROJECT.repository_url` when visibility is
public, otherwise show a `messagebox.showinfo()` message. Add `_show_project_info()`
to show the project metadata and latest update state.

- [ ] **Step 5: Add update check worker**

Start a daemon thread after UI construction. The worker calls
`self.github_client.check_for_update(get_version())` and posts
`("update_check_done", result)` or `("update_check_error", message)` to
`self.msg_queue`.

- [ ] **Step 6: Add update download worker**

The update button starts a daemon thread that downloads the selected asset to
`self.service.base_dir / "aktualizacje"` and posts progress and completion to
`self.msg_queue`.

- [ ] **Step 7: Extend queue polling**

Handle `update_check_done`, `update_check_error`, `update_download_progress`,
`update_download_done`, and `update_download_error`. Show/hide the update button
and animate it through `root.after()`.

- [ ] **Step 8: Manual GUI smoke test**

Run: `python -m intrastat_generator`

Expected: the window opens with icons, GitHub/info controls, existing generation
controls still visible, and no startup exception.

- [ ] **Step 9: Commit**

```bash
git add src/intrastat_generator/gui.py
git commit -m "Add repository and update controls to GUI"
```

---

### Task 6: Release Workflow Icon Bundling

**Files:**
- Modify: `.github/workflows/release.yml`
- Modify: `tests/test_release_workflow.py`

- [ ] **Step 1: Write failing workflow test**

```python
def test_windows_build_jobs_stage_icon_resources_and_apply_exe_icon():
    workflow = release_workflow_text()

    for job_name in ["build-self-hosted", "build-github-hosted"]:
        block = job_block(workflow, job_name)
        build_step = block[block.index("- name: Build EXE") :]

        assert "build/pyinstaller-resources/Icon" in block
        assert "Icon/icon.ico" in block
        assert "build/pyinstaller-resources/Icon;Icon" in build_step
        assert "--icon" in build_step
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_release_workflow.py::test_windows_build_jobs_stage_icon_resources_and_apply_exe_icon -v`

Expected: FAIL because the workflow does not mention Icon resources or `--icon`.

- [ ] **Step 3: Modify workflow**

In each `Stage bundled resources` step, copy `Icon` to
`build/pyinstaller-resources/Icon` when it exists. In each `Build EXE` step, add
`--add-data "build/pyinstaller-resources/Icon;Icon"` when staged and add
`--icon "Icon/icon.ico"` when the source icon exists.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_release_workflow.py::test_windows_build_jobs_stage_icon_resources_and_apply_exe_icon -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_release_workflow.py .github/workflows/release.yml
git commit -m "Bundle icons in release builds"
```

---

### Task 7: Full Verification

**Files:**
- All modified files.

- [ ] **Step 1: Run focused tests**

Run: `python -m pytest tests/test_project_metadata.py tests/test_assets.py tests/test_updater.py tests/test_release_workflow.py -v`

Expected: PASS.

- [ ] **Step 2: Run full test suite**

Run: `python -m pytest`

Expected: PASS.

- [ ] **Step 3: Check working tree**

Run: `git status --short`

Expected: only intentional uncommitted changes remain, or clean if all task
commits were created.
