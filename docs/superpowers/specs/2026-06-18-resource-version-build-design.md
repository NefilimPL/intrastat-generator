# Resource Detection And Versioned EXE Design

## Context

The application currently creates the default `slowniki` directory even when a
valid dictionary folder already exists next to the program, such as `Slowniki`
or `Slowniki` with Polish characters. Tariff guessing only checks for
`taryfa.txt` in the application directory and does not check the bundled
`Taryfa/` folder.

Release builds set `INTRASTAT_GENERATOR_VERSION` to the GitHub ref name, but the
runtime version only includes the tag and falls back to `0.0.0-dev` when the
value is not injected. The PyInstaller command also does not embed Windows EXE
metadata and does not bundle dictionary/tariff resources.

## Goals

- Detect existing dictionary and tariff resource locations automatically.
- Prefer existing resource folders over creating a new empty folder.
- Normalize saved/displayed resource paths to forward slashes.
- Show a build version in the GUI as `<tag>-<branch>`, for example
  `v0.0.5-dev` or `v0.0.6-Main`.
- Add Windows metadata to the generated EXE.
- Bundle `Slowniki`/`Taryfa` resources into release EXEs when those folders
  exist in the repository checkout.

## Non-Goals

- No installer.
- No resource downloads.
- No change to tariff parsing rules or dictionary XML parsing.
- No release publishing behavior change beyond build inputs and artifact names.

## Design

Resource location rules live in `src/intrastat_generator/paths.py` and are used
by `GeneratorService`. The service will choose a dictionary directory by first
respecting a configured path if it exists and contains dictionary files, then by
checking known sibling folder names, then by falling back to the configured
default. Tariff guessing will check configured paths, app-dir files, and
`Taryfa/` files.

Path values written to `config.json` use POSIX-style slashes via `Path.as_posix()`
after resolving relative paths. The loader still accepts Windows-style input
paths because `pathlib.Path` handles them on Windows.

Version resolution will prefer `INTRASTAT_GENERATOR_VERSION`, then combine tag
and branch values from environment variables. GitHub Actions will compute and
export the final version before tests and PyInstaller builds. The branch segment
is the branch that produced the build; for tag builds, the workflow will use the
best available branch name from GitHub context and git branch detection.

EXE metadata is generated during the release workflow into a temporary
PyInstaller version-info file and passed with `--version-file`. The workflow also
passes `--add-data` entries for the repository resource folders so the EXE can
extract them into the PyInstaller runtime directory.

## Testing

Unit tests cover dictionary directory selection, tariff guessing, path
normalization, version formatting, and release workflow text expectations for
version metadata and bundled resources. Existing workbook/tariff tests continue
to cover generation behavior.
