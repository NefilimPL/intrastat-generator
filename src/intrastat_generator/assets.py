from __future__ import annotations

import sys
from pathlib import Path


class AppAssets:
    def __init__(self, app_dir: Path):
        self.app_dir = Path(app_dir)

    @property
    def app_icon_png(self) -> Path | None:
        return self._first_existing("Icon/icon.png")

    @property
    def github_icon_png(self) -> Path | None:
        return self._first_existing("Icon/github.png")

    @property
    def app_icon_ico(self) -> Path | None:
        return self._first_existing("Icon/icon.ico")

    def _first_existing(self, relative: str) -> Path | None:
        for root in self._roots():
            candidate = root / relative
            if candidate.is_file():
                return candidate
        return None

    def _roots(self) -> list[Path]:
        roots = []
        bundle_dir = getattr(sys, "_MEIPASS", "")
        if bundle_dir:
            roots.append(Path(bundle_dir))
        roots.append(self.app_dir)

        unique: dict[str, Path] = {}
        for root in roots:
            key = str(root.resolve()).lower() if root.exists() else str(root.absolute()).lower()
            unique.setdefault(key, root)
        return list(unique.values())
