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
