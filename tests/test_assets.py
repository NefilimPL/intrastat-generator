from __future__ import annotations

import sys
from pathlib import Path


def test_assets_find_source_icon_files(tmp_path: Path):
    from intrastat_generator.assets import AppAssets

    icon_dir = tmp_path / "Icon"
    icon_dir.mkdir()
    app_icon = icon_dir / "icon.png"
    github_icon = icon_dir / "github.png"
    app_ico = icon_dir / "icon.ico"
    app_icon.write_bytes(b"png")
    github_icon.write_bytes(b"png")
    app_ico.write_bytes(b"ico")

    assets = AppAssets(tmp_path)

    assert assets.app_icon_png == app_icon
    assert assets.github_icon_png == github_icon
    assert assets.app_icon_ico == app_ico


def test_assets_find_bundled_icon_files(tmp_path: Path, monkeypatch):
    from intrastat_generator.assets import AppAssets

    app_dir = tmp_path / "app"
    bundle_dir = tmp_path / "bundle"
    icon_dir = bundle_dir / "Icon"
    icon_dir.mkdir(parents=True)
    app_icon = icon_dir / "icon.png"
    github_icon = icon_dir / "github.png"
    app_ico = icon_dir / "icon.ico"
    app_icon.write_bytes(b"png")
    github_icon.write_bytes(b"png")
    app_ico.write_bytes(b"ico")
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)

    assets = AppAssets(app_dir)

    assert assets.app_icon_png == app_icon
    assert assets.github_icon_png == github_icon
    assert assets.app_icon_ico == app_ico


def test_assets_return_none_when_icon_file_is_missing(tmp_path: Path):
    from intrastat_generator.assets import AppAssets

    assets = AppAssets(tmp_path)

    assert assets.app_icon_png is None
    assert assets.github_icon_png is None
    assert assets.app_icon_ico is None
