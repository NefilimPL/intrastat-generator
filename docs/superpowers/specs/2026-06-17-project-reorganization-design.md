# Project Reorganization Design

## Goal

Reorganize the current single-file INTRASTAT generator into a maintainable Python package, add deterministic naming for generated files and release artifacts, and prepare GitHub tag-based EXE releases with self-hosted runner preference and GitHub-hosted fallback.

## Current State

The repository currently contains one main application file, `intrastat_generator_gui_v3_3.py`, plus runtime input data directories:

- `Słowniki/` with XML dictionaries.
- `Taryfa/` with tariff data.
- `DO ZROBIENIA.txt` with pending project notes.

There is no `.gitignore`, no package metadata, no automated test layout, and no GitHub Actions release workflow.

The application writes runtime files next to the executable or source file:

- `config.json`
- `koszty_transportu.json`
- `logi/`
- `wygenerowane_xlsx/`

These runtime outputs must not be tracked by git.

## Target Layout

The project will be reorganized into this package layout:

```text
intrastat-generator/
  src/
    intrastat_generator/
      __init__.py
      __main__.py
      app.py
      cli.py
      config.py
      paths.py
      naming.py
      version.py
      dictionaries.py
      tariff.py
      parser.py
      cn.py
      transport.py
      workbook.py
      service.py
      gui.py
  tests/
    test_naming.py
    test_version.py
  .github/
    workflows/
      release.yml
  requirements.txt
  requirements-dev.txt
  pyproject.toml
  README.md
  .gitignore
```

The old top-level `intrastat_generator_gui_v3_3.py` will be replaced by package entry points. If a compatibility wrapper is kept, it will only import and call `intrastat_generator.cli.main`.

## Module Responsibilities

`__main__.py`
: Enables `python -m intrastat_generator`.

`app.py`
: Tiny application entry point that calls the CLI main function.

`cli.py`
: Owns command-line argument parsing, GUI/no-GUI branching, error reporting, and process exit codes.

`config.py`
: Owns config constants, defaults, JSON load/save helpers, route cost config filenames, and app-level option defaults.

`paths.py`
: Owns base directory detection for frozen EXE vs source execution, relative path resolution, and runtime directory creation.

`naming.py`
: Owns all generated filename logic:

- XLSX names: `INTRASTAT_<nr-deklaracji>_<rok>-<miesiac>_<YYYYMMDD-HHMMSS>.xlsx`
- EXE release names: `Intrastat-Generator_<tag>_Windows_x64.exe`
- filesystem-safe normalization
- collision suffixes such as `_1`, `_2`

`version.py`
: Owns version discovery for GUI, CLI, workbook metadata, and release build naming. Version priority:

1. Explicit build environment value such as `INTRASTAT_GENERATOR_VERSION`.
2. GitHub tag value from `GITHUB_REF_NAME` when it starts with `v`.
3. Local package fallback such as `0.0.0-dev`.

`dictionaries.py`
: Owns dictionary XML discovery and parsing.

`tariff.py`
: Owns tariff text parsing.

`parser.py`
: Owns INTRASTAT XML parsing and `IntrastatItem`.

`cn.py`
: Owns CN code matching, description normalization, and confidence statuses.

`transport.py`
: Owns transport route config, defaults, and statistical value calculation.

`workbook.py`
: Owns XLSX workbook construction, styles, validation sheets, audit sheets, workbook metadata, and save/open verification.

`service.py`
: Owns the generation workflow: load config, load dictionaries, load tariff, parse XML, calculate CN/statistical data, build workbook, and return summary.

`gui.py`
: Owns Tkinter UI, drag-and-drop integration, worker thread handling, status updates, dialogs, and folder-opening actions.

## Naming Requirements

Generated XLSX files must use:

```text
INTRASTAT_<nr-deklaracji>_<rok>-<miesiac>_<YYYYMMDD-HHMMSS>.xlsx
```

Rules:

- Empty declaration number falls back to `INTRASTAT`.
- Empty year or month is omitted safely without leaving awkward duplicate separators.
- Unsafe filesystem characters are replaced with underscores.
- Existing output files are not overwritten; suffixes `_1`, `_2`, and so on are used.

Release EXE files must use:

```text
Intrastat-Generator_<wersja-z-tagu>_Windows_x64.exe
```

Rules:

- For tag `v3.4.0`, the EXE is `Intrastat-Generator_v3.4.0_Windows_x64.exe`.
- Local non-release builds may use fallback version `0.0.0-dev`.

## Versioning Requirements

The GUI title and visible header must use the same version source as the CLI and workbook metadata.

The current mismatch where the application title says v3.3 and the GUI header says v2 must be removed.

The build workflow must pass the GitHub tag into the application build environment so the EXE reports the same version as the release tag.

## Release Workflow Requirements

The workflow will be saved as:

```text
.github/workflows/release.yml
```

Trigger:

- Push tags matching `v*`.
- Manual `workflow_dispatch` is allowed for testing release packaging.

Runner behavior:

1. A lightweight preflight job runs on `ubuntu-latest` and checks repository self-hosted runners through the GitHub API.
2. If an online, non-busy runner with labels `self-hosted`, `Windows`, and `X64` is available, the Windows build runs on that self-hosted runner.
3. If no matching runner is available, the Windows build runs on `windows-latest`.
4. If the self-hosted build is selected but fails, a GitHub-hosted retry job runs on `windows-latest`.

Build behavior:

- Install Python.
- Install runtime and build dependencies.
- Run tests.
- Build a one-file Windows EXE with PyInstaller from `src/intrastat_generator/__main__.py`.
- Rename the output to `Intrastat-Generator_<tag>_Windows_x64.exe`.
- Publish the EXE to the GitHub Release for the tag.

This preflight does not build anything on GitHub-hosted infrastructure before checking self-hosted availability. It only queries runner status so the build can avoid being stuck behind an unavailable self-hosted runner.

## Gitignore Requirements

`.gitignore` must cover files created during normal app usage and build/test runs:

```text
config.json
koszty_transportu.json
logi/
wygenerowane_xlsx/
build/
dist/
*.spec
__pycache__/
*.py[cod]
.pytest_cache/
.coverage
htmlcov/
.venv/
venv/
```

It should also ignore local editor and OS noise without hiding repository source data directories.

## Testing Requirements

Add focused tests before implementation for:

- XLSX filename generation from declaration number, year, month, and timestamp.
- Unsafe character normalization.
- Existing-file collision suffix behavior.
- EXE artifact name generation from a tag.
- Version resolution from explicit env value, GitHub tag env value, and fallback.

After the reorganization, run:

```powershell
python -m pytest
python -m intrastat_generator --help
```

If dependency installation is unavailable in the sandbox, document the exact command that failed and the verification that could not be completed.

## Migration Strategy

The reorganization should preserve behavior while moving code:

1. Add package metadata, `.gitignore`, and tests for the new naming/version units.
2. Implement `naming.py` and `version.py` to satisfy the tests.
3. Move code from the old monolithic file into focused modules.
4. Update imports and entry points.
5. Update GUI labels and workbook metadata to use `version.py`.
6. Add the release workflow.
7. Run tests and CLI help verification.

Large behavior changes unrelated to packaging, naming, versioning, and release automation are out of scope.

## Open Decisions Resolved

- The project will use the full package reorganization approach rather than a minimal workflow-only update.
- The release artifact will keep the leading `v` from the GitHub tag.
- The self-hosted runner is preferred before `windows-latest`.
- Runtime-generated files are ignored by git.
