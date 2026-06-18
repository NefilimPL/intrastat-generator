# Tariff Year Selection Design

## Context

The application currently loads every CN tariff entry from the selected `taryfa.txt`
file through `TariffLoader.load()`. The bundled tariff file contains multiple
year sections marked with top-level headers such as:

- `TARYFA 2026`
- `TARYFA 2025`
- `TARYFA 2024`

The current loader does not expose those years to the GUI and deduplicates tariff
entries across the whole file. That makes it impossible to choose an older tariff
year when generating a declaration for a previous period, for example in January
for December.

## Goal

Add a GUI setting that lets the user choose one of the tariff years available in
the selected tariff text file.

The default selection is the highest year detected in the file. In the GUI that
highest year is shown with an `-Obecny` suffix, for example `2026-Obecny`.
Older years are shown as plain years, for example `2025` and `2024`.

## Non-Goals

- Do not download tariff files.
- Do not infer the tariff year from the declaration XML year or month.
- Do not hard-code specific years in application logic.
- Do not change CN matching thresholds or workbook import columns.

## User Experience

The file section in the GUI gains a readonly combobox labelled `Rocznik taryfy`.
It is populated from the currently selected tariff file.

For a file with `TARYFA 2026`, `TARYFA 2025`, and `TARYFA 2024`, the list is:

```text
2026-Obecny
2025
2024
```

When the application starts, or when a tariff file is selected, the GUI scans the
file for available years. If the user previously saved a specific year and that
year still exists in the file, it remains selected. If no specific year is saved,
or if the saved year is not present in the file, the GUI selects the highest
available year.

If no tariff year headers are found, the combobox is disabled or left empty and
generation falls back to the current behavior of loading the entire file. This
keeps compatibility with single-year or older tariff files that do not include
`TARYFA YYYY` headers.

## Architecture

`src/intrastat_generator/tariff.py`
: Owns tariff year detection and year-filtered tariff loading.

`src/intrastat_generator/service.py`
: Exposes available tariff years for the GUI and passes the selected year into
  the tariff loader during generation.

`src/intrastat_generator/gui.py`
: Owns the `Rocznik taryfy` combobox, refreshes it when the tariff file changes,
  saves the selected year, and sends it to generation through config.

`src/intrastat_generator/config.py`
: Adds a new default config field named `tariff_year`. Empty value means
  auto-select the highest available year from the file. Non-empty value stores
  a manually selected older raw year, for example `2025`, not the GUI label.

`src/intrastat_generator/workbook.py`
: Writes the selected tariff year into the `Ustawienia` sheet for auditability.

## Data Flow

1. GUI starts and resolves the tariff path.
2. GUI asks the service for available tariff years in that file.
3. The service scans top-level headers matching `^\s*TARYFA\s+(\d{4})\s*$`.
4. GUI sorts years descending and displays the highest year as `<year>-Obecny`.
5. GUI stores an empty config value when the selected label is the highest
   `<year>-Obecny` option, preserving automatic current-year behavior for future
   tariff files. If the user selects an older year, GUI stores that raw year
   value in config, for example `2025`.
6. During generation, the service resolves the effective tariff year:
   - saved year if it exists in the file,
   - otherwise the highest detected year,
   - otherwise no year filter.
7. `TariffLoader` loads only entries between the selected `TARYFA YYYY` header
   and the next tariff-year header.
8. Workbook generation receives only entries from the effective year.
9. The `Ustawienia` sheet records the effective tariff year.

## Error Handling

If the tariff file path is missing or invalid, the existing validation remains in
place.

If year detection fails because the file cannot be read, the GUI logs the issue
and leaves the year list empty. Generation will still show the existing file
error if the file is invalid.

If the user saved a year that is not present in a newly selected tariff file, the
application silently switches to the highest available year. This is intentional:
the default must always follow the current tariff file.

If a selected year section contains no 8-digit CN entries, generation fails with
an explicit year-aware error such as `Nie udało się wczytać kodów CN z rocznika
taryfy 2025.`

## Tests

Add focused tests for:

- detecting years from multiple `TARYFA YYYY` headers;
- sorting years descending for GUI/service use;
- loading only the selected year section;
- defaulting to the highest available year when no saved year is configured;
- falling back to the highest available year when the saved year is missing;
- loading the full file when no year headers exist;
- preserving existing tariff parsing behavior for code, spaced code,
  description, and path text.

The GUI itself can stay covered through service and tariff unit tests because the
combobox behavior is a thin Tkinter binding around those methods.

## Acceptance Criteria

- A tariff file containing 2026, 2025, and 2024 sections produces the GUI options
  `2026-Obecny`, `2025`, `2024`.
- On first run, the selected year is the highest year in the file.
- If `2025` is saved in config and the selected file still contains `TARYFA 2025`,
  the GUI keeps `2025` selected.
- Selecting `2025` makes generation use only the `TARYFA 2025` section.
- Replacing the tariff file with one containing a higher year automatically moves
  the default/current selection to that higher year when the previous saved value
  is unavailable.
- The generated XLSX `Ustawienia` sheet includes the effective tariff year.
- Existing single-year files without `TARYFA YYYY` headers still load.
