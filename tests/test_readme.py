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
