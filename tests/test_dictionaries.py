from __future__ import annotations

from pathlib import Path

from intrastat_generator.dictionaries import DictionaryLoader
from intrastat_generator.service import GeneratorService


def write_dictionary(path: Path, code: str, *values: str) -> None:
    rows = "\n".join(f'  <Pozycja Kod="{value}" Opis="{value}" />' for value in values)
    path.write_text(
        (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<Slownik Kod="{code}" Nazwa="Test" DataEdycji="2026-01-01">\n'
            f"{rows}\n"
            "</Slownik>\n"
        ),
        encoding="utf-8",
    )


def test_dictionary_loader_parses_codes_from_selected_folder(tmp_path):
    dict_dir = tmp_path / "Slowniki"
    dict_dir.mkdir()
    write_dictionary(dict_dir / "slownik002.xml", "002", "EXW", "DAP")

    dictionaries = DictionaryLoader(tmp_path, dict_dir).load()

    assert dictionaries["002"].codes() == ["EXW", "DAP"]


def test_dictionary_loader_finds_dictionaries_inside_selected_parent_folder(tmp_path):
    selected_dir = tmp_path / "dane"
    nested_dict_dir = selected_dir / "Slowniki"
    nested_dict_dir.mkdir(parents=True)
    write_dictionary(nested_dict_dir / "slownik004.xml", "004", "11", "21")

    dictionaries = DictionaryLoader(tmp_path, selected_dir).load()

    assert dictionaries["004"].codes() == ["11", "21"]


def test_service_combobox_values_include_codes_from_configured_dictionary_folder(tmp_path):
    dict_dir = tmp_path / "Slowniki"
    dict_dir.mkdir()
    write_dictionary(dict_dir / "slownik005.xml", "005", "3", "4")
    service = GeneratorService(tmp_path)
    service.config["dict_dir"] = str(dict_dir)

    assert service.dict_codes_for_gui("005") == ["", "3", "4"]
