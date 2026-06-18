# Resource Detection And Versioned EXE Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add automatic dictionary/tariff resource detection and produce EXEs whose GUI/version metadata use `<tag>-<branch>`.

**Architecture:** `paths.py` owns path normalization and resource discovery. `service.py` uses those helpers for config defaults and tariff guessing. `version.py` owns version composition from environment values. The GitHub release workflow computes the build version once, passes it to tests/PyInstaller, bundles data folders, and supplies a generated Windows version-info file.

**Tech Stack:** Python 3.11, pathlib, pytest, PyInstaller, GitHub Actions on Windows.

---

## Files

- Modify: `src/intrastat_generator/paths.py`
- Modify: `src/intrastat_generator/service.py`
- Modify: `src/intrastat_generator/version.py`
- Modify: `.github/workflows/release.yml`
- Modify: `tests/test_paths.py`
- Modify: `tests/test_version.py`
- Modify: `tests/test_release_workflow.py`
- Optionally modify: `tests/test_dictionaries.py`

## Task 1: Resource Path Tests

- [ ] Add failing tests in `tests/test_paths.py` for forward-slash normalization, existing dictionary folder preference, and fallback directory creation behavior.

```python
def test_format_config_path_uses_forward_slashes(tmp_path):
    path = tmp_path / "folder" / "child"
    assert format_config_path(path) == path.as_posix()


def test_select_dictionary_dir_prefers_existing_slowniki_folder(tmp_path):
    existing = tmp_path / "Slowniki"
    existing.mkdir()
    (existing / "slownik002.xml").write_text("<Slownik Kod='002' />", encoding="utf-8")

    assert select_dictionary_dir(tmp_path, "slowniki") == existing


def test_ensure_dirs_does_not_create_default_when_existing_dictionary_folder_is_found(tmp_path):
    existing = tmp_path / "Slowniki"
    existing.mkdir()
    (existing / "slownik002.xml").write_text("<Slownik Kod='002' />", encoding="utf-8")

    paths = ensure_dirs(tmp_path, {"dict_dir": "slowniki", "output_dir": "out"})

    assert paths["dict"] == existing
    assert not (tmp_path / "slowniki").exists()
```

- [ ] Run `pytest tests/test_paths.py -q` and confirm the new tests fail because the helper functions do not exist or behavior is not implemented.

- [ ] Implement `format_config_path`, `directory_contains_dictionaries`, `select_dictionary_dir`, and update `ensure_dirs` to use them.

- [ ] Run `pytest tests/test_paths.py -q` and confirm it passes.

## Task 2: Tariff Guessing Tests

- [ ] Add failing tests in `tests/test_paths.py` or `tests/test_dictionaries.py` for tariff discovery in `Taryfa/taryfa.txt` and config path normalization.

```python
def test_service_guesses_tariff_inside_taryfa_folder(tmp_path):
    tariff_dir = tmp_path / "Taryfa"
    tariff_dir.mkdir()
    tariff = tariff_dir / "taryfa.txt"
    tariff.write_text("", encoding="utf-8")

    service = GeneratorService(tmp_path)

    assert service.guess_tariff_path() == tariff.as_posix()
    assert service.config["tariff_path"] == tariff.as_posix()
```

- [ ] Run the focused test and confirm it fails.

- [ ] Update `GeneratorService.guess_tariff_path()` to check configured path, app-dir files, and `Taryfa/` files, and save POSIX-style paths.

- [ ] Run the focused test and confirm it passes.

## Task 3: Version Composition Tests

- [ ] Add failing tests in `tests/test_version.py` for `tag-branch` composition.

```python
def test_resolve_version_combines_tag_and_branch():
    env = {"GITHUB_REF_NAME": "v0.0.5", "INTRASTAT_GENERATOR_BRANCH": "dev"}
    assert resolve_version(env) == "v0.0.5-dev"


def test_resolve_version_uses_branch_for_non_tag_build():
    env = {"GITHUB_REF_NAME": "feature-x", "INTRASTAT_GENERATOR_BRANCH": "feature-x"}
    assert resolve_version(env) == "0.0.0-feature-x"
```

- [ ] Run `pytest tests/test_version.py -q` and confirm the new tests fail.

- [ ] Update `src/intrastat_generator/version.py` to compose versions from `INTRASTAT_GENERATOR_VERSION`, `GITHUB_REF_NAME`, and `INTRASTAT_GENERATOR_BRANCH`.

- [ ] Run `pytest tests/test_version.py -q` and confirm it passes.

## Task 4: Release Workflow Tests

- [ ] Extend `tests/test_release_workflow.py` to assert that both Windows build jobs compute `INTRASTAT_GENERATOR_BRANCH`, compute `INTRASTAT_GENERATOR_VERSION`, pass `--version-file`, and pass `--add-data` for dictionary and tariff folders.

- [ ] Run `pytest tests/test_release_workflow.py -q` and confirm it fails.

- [ ] Update `.github/workflows/release.yml` so each Windows job has a build-version step before tests and a generated PyInstaller version file before `Build EXE`.

- [ ] Update each PyInstaller command to include `--version-file`, `--add-data "Slowniki;Slowniki"` or the actual existing dictionary folder, and `--add-data "Taryfa;Taryfa"` when those folders exist.

- [ ] Run `pytest tests/test_release_workflow.py -q` and confirm it passes.

## Task 5: Full Verification

- [ ] Run `pytest -q`.

- [ ] Inspect `git diff --stat` and `git diff --check`.

- [ ] Report changed files, verification results, and any skipped build verification.
