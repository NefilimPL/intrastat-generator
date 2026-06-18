from __future__ import annotations

import sys
from pathlib import Path

from intrastat_generator.paths import ensure_dirs, format_config_path, get_app_dir, select_dictionary_dir
from intrastat_generator.service import GeneratorService
from intrastat_generator.gui import format_gui_path


def test_source_app_dir_is_project_root_not_package_dir():
    root = Path(__file__).resolve().parents[1]

    assert get_app_dir() == root


def test_format_config_path_uses_forward_slashes(tmp_path: Path):
    path = tmp_path / "folder" / "child"

    assert format_config_path(path) == path.as_posix()


def test_format_gui_path_uses_forward_slashes(tmp_path: Path):
    path = tmp_path / "folder" / "slowniki"

    assert format_gui_path(path) == path.as_posix()


def test_select_dictionary_dir_prefers_existing_slowniki_folder(tmp_path: Path):
    existing = tmp_path / "Slowniki"
    existing.mkdir()
    (existing / "slownik002.xml").write_text("<Slownik Kod='002' />", encoding="utf-8")

    assert select_dictionary_dir(tmp_path, "slowniki") == existing


def test_ensure_dirs_does_not_create_default_when_existing_dictionary_folder_is_found(tmp_path: Path):
    existing = tmp_path / "Slowniki"
    existing.mkdir()
    (existing / "slownik002.xml").write_text("<Slownik Kod='002' />", encoding="utf-8")

    paths = ensure_dirs(tmp_path, {"dict_dir": "slowniki", "output_dir": "out"})

    assert paths["dict"] == existing
    assert paths["dict"].samefile(existing)


def test_service_guesses_tariff_inside_taryfa_folder(tmp_path: Path):
    tariff_dir = tmp_path / "Taryfa"
    tariff_dir.mkdir()
    tariff = tariff_dir / "taryfa.txt"
    tariff.write_text("", encoding="utf-8")

    service = GeneratorService(tmp_path)

    assert service.guess_tariff_path() == tariff.as_posix()
    assert service.config["tariff_path"] == tariff.as_posix()


def test_ensure_dirs_copies_bundled_dictionary_folder_when_no_external_files(tmp_path: Path, monkeypatch):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    bundle_dir = tmp_path / "bundle"
    bundled_dict_dir = bundle_dir / "Słowniki"
    bundled_dict_dir.mkdir(parents=True)
    (bundled_dict_dir / "slownik002.xml").write_text("<Slownik Kod='002' />", encoding="utf-8")
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)

    paths = ensure_dirs(app_dir, {"dict_dir": "slowniki", "output_dir": "out"})

    copied = app_dir / "Słowniki" / "slownik002.xml"
    assert copied.exists()
    assert paths["dict"] == app_dir / "Słowniki"


def test_service_copies_bundled_tariff_folder_and_uses_local_copy(tmp_path: Path, monkeypatch):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    bundle_dir = tmp_path / "bundle"
    bundled_tariff_dir = bundle_dir / "Taryfa"
    bundled_tariff_dir.mkdir(parents=True)
    (bundled_tariff_dir / "taryfa.txt").write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)

    service = GeneratorService(app_dir)

    tariff = app_dir / "Taryfa" / "taryfa.txt"
    assert tariff.exists()
    assert service.guess_tariff_path() == tariff.as_posix()
