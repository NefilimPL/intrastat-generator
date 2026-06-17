from __future__ import annotations

from pathlib import Path

from intrastat_generator.paths import get_app_dir


def test_source_app_dir_is_project_root_not_package_dir():
    root = Path(__file__).resolve().parents[1]

    assert get_app_dir() == root
