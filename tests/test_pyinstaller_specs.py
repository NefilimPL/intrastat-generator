from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC_FILES = ["intrastat-generator.spec", "intrastat-generator-test.spec"]


def spec_text(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_pyinstaller_specs_use_application_icon():
    for name in SPEC_FILES:
        text = spec_text(name)

        assert "icon='Icon\\\\icon.ico'" in text


def test_pyinstaller_specs_bundle_icon_folder():
    for name in SPEC_FILES:
        text = spec_text(name)

        assert "('Icon', 'Icon')" in text
