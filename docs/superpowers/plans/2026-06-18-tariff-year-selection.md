# Tariff Year Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add tariff-year detection and selection from multi-year `taryfa.txt` files, defaulting to the highest available year.

**Architecture:** `tariff.py` detects `TARYFA YYYY` headers and can load a single year section. `service.py` resolves the effective year, exposes GUI labels, and converts the selected current year to an empty auto config value. `gui.py` binds a readonly year combobox to config, and `workbook.py` records the effective year in `Ustawienia`.

**Tech Stack:** Python 3.11, pytest, Tkinter, openpyxl.

**User Constraint:** Do not commit implementation changes automatically. This plan intentionally omits commit steps.

---

### Task 1: Tariff Year Detection And Filtering

**Files:**
- Modify: `src/intrastat_generator/tariff.py`
- Modify: `src/intrastat_generator/models.py`
- Test: `tests/test_tariff.py`

- [ ] **Step 1: Write failing tariff tests**

Create `tests/test_tariff.py` with tests that write small tariff fixtures:

```python
from __future__ import annotations

from pathlib import Path

from intrastat_generator.tariff import TariffLoader


def write_tariff(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def test_tariff_loader_detects_years_descending(tmp_path):
    tariff = tmp_path / "taryfa.txt"
    write_tariff(
        tariff,
        """
TARYFA 2025
    9401 10 00 - Seats 2025
TARYFA 2026
    9401 10 00 - Seats 2026
TARYFA 2024
    9401 10 00 - Seats 2024
""",
    )

    assert TariffLoader(tariff).available_years() == ["2026", "2025", "2024"]


def test_tariff_loader_loads_only_selected_year_section(tmp_path):
    tariff = tmp_path / "taryfa.txt"
    write_tariff(
        tariff,
        """
TARYFA 2026
    9401 10 00 - Seats current
TARYFA 2025
    9401 10 00 - Seats previous
    9403 20 00 - Metal furniture previous
TARYFA 2024
    9401 10 00 - Seats old
""",
    )

    entries = TariffLoader(tariff, year="2025").load()

    assert [entry.code for entry in entries] == ["94011000", "94032000"]
    assert {entry.year for entry in entries} == {"2025"}
    assert entries[0].description == "Seats previous"


def test_tariff_loader_without_year_headers_loads_entire_file(tmp_path):
    tariff = tmp_path / "taryfa.txt"
    write_tariff(
        tariff,
        """
MEBLE
    9401 10 00 - Seats
    9403 20 00 - Metal furniture
""",
    )

    entries = TariffLoader(tariff, year="2026").load()

    assert [entry.code for entry in entries] == ["94011000", "94032000"]
    assert {entry.year for entry in entries} == {""}
```

- [ ] **Step 2: Run tariff tests and verify RED**

Run:

```bash
pytest tests/test_tariff.py -q
```

Expected: fails because `available_years`, `TariffLoader(..., year=...)`, and `TariffEntry.year` do not exist yet.

- [ ] **Step 3: Implement minimal tariff support**

Update `TariffEntry` with a `year: str = ""` field.

Update `TariffLoader`:

```python
YEAR_RE = re.compile(r"^\s*TARYFA\s+(\d{4})\s*$")

def __init__(self, tariff_path: Path, year: str = ""):
    self.tariff_path = tariff_path
    self.year = str(year or "").strip()

def available_years(self) -> List[str]:
    years = set()
    with self.tariff_path.open("r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            match = self.YEAR_RE.match(raw.strip())
            if match:
                years.add(match.group(1))
    return sorted(years, reverse=True)
```

In `load()`, track `current_year`, clear context when entering a new year, and skip tariff/content lines outside `self.year` when year headers exist. If the file has no year headers, load the entire file as before.

- [ ] **Step 4: Run tariff tests and verify GREEN**

Run:

```bash
pytest tests/test_tariff.py -q
```

Expected: all tariff tests pass.

### Task 2: Service Year Resolution And GUI Labels

**Files:**
- Modify: `src/intrastat_generator/config.py`
- Modify: `src/intrastat_generator/service.py`
- Test: `tests/test_tariff.py`

- [ ] **Step 1: Write failing service tests**

Append to `tests/test_tariff.py`:

```python
from intrastat_generator.service import GeneratorService


def test_service_formats_tariff_year_options_with_current_suffix(tmp_path):
    tariff = tmp_path / "taryfa.txt"
    write_tariff(
        tariff,
        """
TARYFA 2026
    9401 10 00 - Seats current
TARYFA 2025
    9401 10 00 - Seats previous
""",
    )
    service = GeneratorService(tmp_path)

    assert service.tariff_year_options(tariff) == [("2026-Obecny", "2026"), ("2025", "2025")]


def test_service_selects_highest_tariff_year_by_default(tmp_path):
    tariff = tmp_path / "taryfa.txt"
    write_tariff(
        tariff,
        """
TARYFA 2024
    9401 10 00 - Seats old
TARYFA 2026
    9401 10 00 - Seats current
""",
    )
    service = GeneratorService(tmp_path)
    service.config["tariff_year"] = ""

    assert service.resolve_tariff_year(tariff) == "2026"


def test_service_keeps_saved_tariff_year_when_available(tmp_path):
    tariff = tmp_path / "taryfa.txt"
    write_tariff(
        tariff,
        """
TARYFA 2026
    9401 10 00 - Seats current
TARYFA 2025
    9401 10 00 - Seats previous
""",
    )
    service = GeneratorService(tmp_path)
    service.config["tariff_year"] = "2025"

    assert service.resolve_tariff_year(tariff) == "2025"


def test_service_saves_empty_config_value_for_current_tariff_year(tmp_path):
    tariff = tmp_path / "taryfa.txt"
    write_tariff(
        tariff,
        """
TARYFA 2026
    9401 10 00 - Seats current
TARYFA 2025
    9401 10 00 - Seats previous
""",
    )
    service = GeneratorService(tmp_path)

    assert service.tariff_year_config_value(tariff, "2026") == ""
    assert service.tariff_year_config_value(tariff, "2025") == "2025"
```

- [ ] **Step 2: Run service tests and verify RED**

Run:

```bash
pytest tests/test_tariff.py -q
```

Expected: fails because `tariff_year_options`, `resolve_tariff_year`, `tariff_year_config_value`, and default `tariff_year` do not exist.

- [ ] **Step 3: Implement service helpers**

Add `"tariff_year": ""` to `DEFAULT_CONFIG`.

Add service methods:

```python
def available_tariff_years(self, tariff_path: Path) -> List[str]:
    return TariffLoader(tariff_path).available_years()

def tariff_year_options(self, tariff_path: Path) -> List[Tuple[str, str]]:
    years = self.available_tariff_years(tariff_path)
    if not years:
        return []
    current = years[0]
    return [(f"{year}-Obecny" if year == current else year, year) for year in years]

def resolve_tariff_year(self, tariff_path: Path) -> str:
    years = self.available_tariff_years(tariff_path)
    if not years:
        return ""
    configured = norm_text(self.config.get("tariff_year", ""))
    return configured if configured in years else years[0]

def tariff_year_config_value(self, tariff_path: Path, selected_year: str) -> str:
    years = self.available_tariff_years(tariff_path)
    selected = norm_text(selected_year)
    if not years or selected not in years or selected == years[0]:
        return ""
    return selected
```

Update `generate()` to use `effective_tariff_year = self.resolve_tariff_year(tariff_path)`, save it in config, load `TariffLoader(tariff_path, year=effective_tariff_year)`, and include `tariff_year` in the returned summary/config.

- [ ] **Step 4: Run service tests and verify GREEN**

Run:

```bash
pytest tests/test_tariff.py -q
```

Expected: all tariff/service tests pass.

### Task 3: GUI Combobox Binding

**Files:**
- Modify: `src/intrastat_generator/gui.py`

- [ ] **Step 1: Add year state and refresh methods**

Add `self.tariff_year_var = tk.StringVar()` and `self.tariff_year_values: Dict[str, str] = {}` during initialization.

Add methods:

```python
def _refresh_tariff_years(self) -> None:
    tariff = Path(self.tariff_var.get().strip().strip('"'))
    self.tariff_year_values = {}
    if not str(tariff) or not tariff.exists():
        self.tariff_year_combo.configure(values=[], state="disabled")
        self.tariff_year_var.set("")
        return
    options = self.service.tariff_year_options(tariff)
    labels = [label for label, _year in options]
    self.tariff_year_values = dict(options)
    if not labels:
        self.tariff_year_combo.configure(values=[], state="disabled")
        self.tariff_year_var.set("")
        return
    selected = self.service.resolve_tariff_year(tariff)
    selected_label = next((label for label, year in options if year == selected), labels[0])
    self.tariff_year_combo.configure(values=labels, state="readonly")
    self.tariff_year_var.set(selected_label)

def _selected_tariff_year(self) -> str:
    return self.tariff_year_values.get(self.tariff_year_var.get(), "")
```

- [ ] **Step 2: Add combobox to file section**

Add a `Rocznik taryfy` label and readonly combobox in the file section, using the next grid row after tariff file selection. Shift the dictionary directory row down by one.

Bind the tariff path entry or file selection flow so selecting a new tariff file calls `_refresh_tariff_years()`.

- [ ] **Step 3: Persist selected year**

Update `_save_options_to_config()` to save:

```python
self.service.config["tariff_year"] = self._selected_tariff_year()
```

Update `_generate_clicked()` to refresh years before saving and generating.

### Task 4: Workbook Audit Field

**Files:**
- Modify: `src/intrastat_generator/workbook.py`
- Test: `tests/test_workbook.py`

- [ ] **Step 1: Write failing workbook test**

Extend `tests/test_workbook.py` so its workbook config includes `"tariff_year": "2025"` and assert that the `Ustawienia` sheet contains `["Rocznik taryfy", "2025"]`.

- [ ] **Step 2: Run workbook test and verify RED**

Run:

```bash
pytest tests/test_workbook.py -q
```

Expected: fails because the settings row is not written.

- [ ] **Step 3: Add settings row**

In `_write_settings_sheet()`, add:

```python
["Rocznik taryfy", self.config.get("tariff_year", "")],
```

near the loaded tariff count/settings rows.

- [ ] **Step 4: Run workbook test and verify GREEN**

Run:

```bash
pytest tests/test_workbook.py -q
```

Expected: workbook tests pass.

### Task 5: Final Verification

**Files:**
- All modified source/tests/docs.

- [ ] **Step 1: Run focused tests**

Run:

```bash
pytest tests/test_tariff.py tests/test_workbook.py -q
```

Expected: all focused tests pass.

- [ ] **Step 2: Run full test suite**

Run:

```bash
pytest -q
```

Expected: all tests pass.

- [ ] **Step 3: Inspect working tree**

Run:

```bash
git status --short
```

Expected: implementation files are modified/untracked, no new commits were created after `fc39df6`, and the pre-existing `DO ZROBIENIA.txt` change remains untouched.
