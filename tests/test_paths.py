from __future__ import annotations

import json
import sys
from pathlib import Path

from intrastat_generator.paths import ensure_dirs, format_config_path, get_app_dir, log_exception, select_dictionary_dir
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


def test_service_uses_istat_shared_slowniki_folder_for_resources_and_config(tmp_path: Path):
    shared_dir = tmp_path / "slowniki"
    shared_dir.mkdir()
    (shared_dir / "slownik002.xml").write_text("<Slownik Kod='002' />", encoding="utf-8")
    tariff = shared_dir / "taryfa.txt"
    tariff.write_text("", encoding="utf-8")

    service = GeneratorService(tmp_path)

    config_dir = tmp_path / "Intrastat generator config"
    assert service.config_path == config_dir / "config.json"
    assert service.route_costs_path() == config_dir / "koszty_transportu.json"
    assert service.config["dict_dir"] == shared_dir.as_posix()
    assert service.guess_tariff_path() == tariff.as_posix()
    assert not (tmp_path / "Słowniki").exists()
    assert not (tmp_path / "Taryfa").exists()


def test_service_refreshes_stale_absolute_resource_paths_after_move(tmp_path: Path):
    old_dir = tmp_path / "old-install"
    old_dict_dir = old_dir / "slowniki"
    old_tariff = old_dir / "Taryfa" / "taryfa.txt"
    new_dir = tmp_path / "new-install"
    new_dict_dir = new_dir / "Słowniki"
    new_tariff_dir = new_dir / "Taryfa"
    new_dict_dir.mkdir(parents=True)
    new_tariff_dir.mkdir()
    (new_dict_dir / "slownik002.xml").write_text("<Slownik Kod='002' />", encoding="utf-8")
    new_tariff = new_tariff_dir / "taryfa.txt"
    new_tariff.write_text("", encoding="utf-8")
    (new_dir / "config.json").write_text(
        json.dumps(
            {
                "dict_dir": old_dict_dir.as_posix(),
                "tariff_path": old_tariff.as_posix(),
                "output_dir": "out",
            }
        ),
        encoding="utf-8",
    )

    service = GeneratorService(new_dir)

    assert service.config["dict_dir"] == new_dict_dir.as_posix()
    assert service.config["tariff_path"] == new_tariff.as_posix()
    saved_config = json.loads((new_dir / "config.json").read_text(encoding="utf-8"))
    assert saved_config["dict_dir"] == new_dict_dir.as_posix()
    assert saved_config["tariff_path"] == new_tariff.as_posix()
    assert service.guess_tariff_path() == new_tariff.as_posix()
    assert not old_dict_dir.exists()


def test_select_dictionary_dir_uses_default_when_stale_absolute_path_has_no_files(tmp_path: Path):
    old_dir = tmp_path / "old-install" / "slowniki"
    new_dir = tmp_path / "new-install"
    new_dir.mkdir()

    assert select_dictionary_dir(new_dir, old_dir) == new_dir / "slowniki"


def test_ensure_dirs_uses_existing_old_dictionary_path_before_copying_bundle(tmp_path: Path, monkeypatch):
    old_dict_dir = tmp_path / "old-install" / "slowniki"
    old_dict_dir.mkdir(parents=True)
    (old_dict_dir / "slownik002.xml").write_text("<Slownik Kod='002' />", encoding="utf-8")
    new_dir = tmp_path / "new-install"
    new_dir.mkdir()
    bundle_dir = tmp_path / "bundle"
    bundled_dict_dir = bundle_dir / "Slowniki"
    bundled_dict_dir.mkdir(parents=True)
    (bundled_dict_dir / "slownik004.xml").write_text("<Slownik Kod='004' />", encoding="utf-8")
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)

    paths = ensure_dirs(new_dir, {"dict_dir": old_dict_dir.as_posix(), "output_dir": "out"})

    assert paths["dict"] == old_dict_dir
    assert not (new_dir / "slowniki").exists()
    assert not (old_dict_dir / "slownik004.xml").exists()


def test_service_uses_existing_old_tariff_path_before_copying_bundle(tmp_path: Path, monkeypatch):
    old_tariff_dir = tmp_path / "old-install" / "Taryfa"
    old_tariff_dir.mkdir(parents=True)
    old_tariff = old_tariff_dir / "taryfa.txt"
    old_tariff.write_text("", encoding="utf-8")
    old_dict_dir = tmp_path / "old-install" / "slowniki"
    old_dict_dir.mkdir()
    (old_dict_dir / "slownik002.xml").write_text("<Slownik Kod='002' />", encoding="utf-8")
    new_dir = tmp_path / "new-install"
    new_dir.mkdir()
    bundle_dir = tmp_path / "bundle"
    bundled_tariff_dir = bundle_dir / "Taryfa"
    bundled_tariff_dir.mkdir(parents=True)
    (bundled_tariff_dir / "taryfa(1).txt").write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)
    (new_dir / "config.json").write_text(
        json.dumps(
            {
                "dict_dir": old_dict_dir.as_posix(),
                "tariff_path": old_tariff.as_posix(),
                "output_dir": "out",
            }
        ),
        encoding="utf-8",
    )

    service = GeneratorService(new_dir)

    assert service.config["tariff_path"] == old_tariff.as_posix()
    assert not (new_dir / "Taryfa").exists()


def test_ensure_dirs_copies_bundled_dictionary_folder_when_no_external_files(tmp_path: Path, monkeypatch):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    bundle_dir = tmp_path / "bundle"
    bundled_dict_dir = bundle_dir / "Słowniki"
    bundled_dict_dir.mkdir(parents=True)
    (bundled_dict_dir / "slownik002.xml").write_text("<Slownik Kod='002' />", encoding="utf-8")
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)

    paths = ensure_dirs(app_dir, {"dict_dir": "slowniki", "output_dir": "out"})

    copied = app_dir / "slowniki" / "slownik002.xml"
    child_dirs = {path.name for path in app_dir.iterdir() if path.is_dir()}
    assert copied.exists()
    assert "slowniki" in child_dirs
    assert "Słowniki" not in child_dirs
    assert paths["dict"] == app_dir / "slowniki"


def test_ensure_dirs_copies_staged_pyinstaller_dictionary_files_to_default_slowniki(tmp_path: Path, monkeypatch):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    bundle_dir = tmp_path / "bundle"
    bundled_dict_dir = bundle_dir / "Slowniki"
    bundled_dict_dir.mkdir(parents=True)
    (bundled_dict_dir / "slownik002.xml").write_text("<Slownik Kod='002' />", encoding="utf-8")
    bundled_tariff_dir = bundle_dir / "Taryfa"
    bundled_tariff_dir.mkdir()
    (bundled_tariff_dir / "taryfa.txt").write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)

    paths = ensure_dirs(app_dir, {"dict_dir": "slowniki", "output_dir": "out"})

    child_dirs = {path.name for path in app_dir.iterdir() if path.is_dir()}
    assert (app_dir / "slowniki" / "slownik002.xml").exists()
    assert "slowniki" in child_dirs
    assert "Slowniki" not in child_dirs
    assert paths["dict"] == app_dir / "slowniki"


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


def test_ensure_dirs_does_not_copy_bundled_dictionary_files_when_local_dictionary_exists(tmp_path: Path, monkeypatch):
    app_dir = tmp_path / "app"
    existing_dict_dir = app_dir / "Słowniki"
    existing_dict_dir.mkdir(parents=True)
    existing_dict = existing_dict_dir / "slownik002.xml"
    existing_dict.write_text("custom dictionary", encoding="utf-8")
    bundle_dir = tmp_path / "bundle"
    bundled_dict_dir = bundle_dir / "Słowniki"
    bundled_dict_dir.mkdir(parents=True)
    (bundled_dict_dir / "slownik002.xml").write_text("bundled dictionary", encoding="utf-8")
    (bundled_dict_dir / "slownik004.xml").write_text("missing dictionary", encoding="utf-8")
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)

    paths = ensure_dirs(app_dir, {"dict_dir": "slowniki", "output_dir": "out"})

    assert paths["dict"] == existing_dict_dir
    assert existing_dict.read_text(encoding="utf-8") == "custom dictionary"
    assert not (existing_dict_dir / "slownik004.xml").exists()


def test_ensure_dirs_does_not_copy_bundled_tariff_files_when_local_tariff_exists(tmp_path: Path, monkeypatch):
    app_dir = tmp_path / "app"
    existing_tariff_dir = app_dir / "Taryfa"
    existing_tariff_dir.mkdir(parents=True)
    existing_tariff = existing_tariff_dir / "taryfa.txt"
    existing_tariff.write_text("custom tariff", encoding="utf-8")
    bundle_dir = tmp_path / "bundle"
    bundled_tariff_dir = bundle_dir / "Taryfa"
    bundled_tariff_dir.mkdir(parents=True)
    (bundled_tariff_dir / "taryfa.txt").write_text("bundled tariff", encoding="utf-8")
    (bundled_tariff_dir / "taryfa(1).txt").write_text("missing tariff", encoding="utf-8")
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)

    ensure_dirs(app_dir, {"dict_dir": "slowniki", "output_dir": "out"})

    assert existing_tariff.read_text(encoding="utf-8") == "custom tariff"
    assert not (existing_tariff_dir / "taryfa(1).txt").exists()


def test_ensure_dirs_does_not_copy_bundled_resources_when_istat_slowniki_has_resources(tmp_path: Path, monkeypatch):
    app_dir = tmp_path / "app"
    shared_dir = app_dir / "slowniki"
    shared_dir.mkdir(parents=True)
    (shared_dir / "slownik002.xml").write_text("<Slownik Kod='002' />", encoding="utf-8")
    (shared_dir / "taryfa.txt").write_text("", encoding="utf-8")
    bundle_dir = tmp_path / "bundle"
    bundled_dict_dir = bundle_dir / "Słowniki"
    bundled_dict_dir.mkdir(parents=True)
    (bundled_dict_dir / "slownik004.xml").write_text("<Slownik Kod='004' />", encoding="utf-8")
    bundled_tariff_dir = bundle_dir / "Taryfa"
    bundled_tariff_dir.mkdir(parents=True)
    (bundled_tariff_dir / "taryfa(1).txt").write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)

    paths = ensure_dirs(app_dir, {"dict_dir": "slowniki", "output_dir": "out"})

    config_dir = app_dir / "Intrastat generator config"
    assert paths["dict"] == shared_dir
    assert paths["logs"] == config_dir / "logi"
    assert not (shared_dir / "slownik004.xml").exists()
    assert not (app_dir / "Słowniki").exists()
    assert not (app_dir / "Taryfa").exists()


def test_log_exception_uses_config_folder_in_istat_mode(tmp_path: Path):
    shared_dir = tmp_path / "slowniki"
    shared_dir.mkdir()
    (shared_dir / "slownik002.xml").write_text("<Slownik Kod='002' />", encoding="utf-8")
    (shared_dir / "taryfa.txt").write_text("", encoding="utf-8")

    log_path = log_exception(tmp_path, RuntimeError("boom"))

    assert log_path.parent == tmp_path / "Intrastat generator config" / "logi"
