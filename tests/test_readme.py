from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def readme_text() -> str:
    return (ROOT / "README.md").read_text(encoding="utf-8")


def test_readme_documents_project_repository_and_updates():
    text = readme_text()

    assert "https://github.com/NefilimPL/intrastat-generator" in text
    assert "NefilimPL and contributors" in text
    assert "MIT" in text
    assert "Icon/icon.png" in text
    assert "Icon/github.png" in text
    assert "Update" in text
    assert "releases/latest" in text
    assert "Repozytorium prywatne" in text


def test_readme_displays_project_badges():
    text = readme_text()

    assert "actions/workflows/release.yml/badge.svg" in text
    assert "actions/workflows/release.yml" in text
    assert "img.shields.io/github/v/release/NefilimPL/intrastat-generator" in text
    assert "img.shields.io/github/license/NefilimPL/intrastat-generator" in text
    assert "img.shields.io/badge/python-3.11%2B" in text


def test_readme_explains_intrastat_purpose_and_links_gus():
    text = readme_text()

    assert "Do czego sluzy" in text
    assert "INTRASTAT" in text
    assert "XLSX" in text
    assert "XML" in text
    assert "https://stat.gov.pl/badania-statystyczne/sprawozdawczosc/intrastat/elektroniczne-zgloszenia-intrastat/" in text
