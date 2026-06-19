from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_repository_contains_mit_license():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")

    assert "MIT License" in text
    assert "Permission is hereby granted" in text
    assert "NefilimPL" in text


def test_package_metadata_declares_mit_license_and_authors():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]

    assert project["license"]["text"] == "MIT"
    assert project["authors"] == [{"name": "NefilimPL and contributors"}]


def test_project_metadata_contains_repository_information():
    from intrastat_generator.project import PROJECT

    assert PROJECT.name == "intrastat-generator"
    assert PROJECT.display_name == "Generator INTRASTAT XLSX"
    assert PROJECT.repository_owner == "NefilimPL"
    assert PROJECT.repository_name == "intrastat-generator"
    assert PROJECT.repository_slug == "NefilimPL/intrastat-generator"
    assert PROJECT.repository_url == "https://github.com/NefilimPL/intrastat-generator"
    assert PROJECT.description == "Generator XLSX INTRASTAT"
    assert PROJECT.authors == "NefilimPL and contributors"
    assert PROJECT.license == "MIT"
