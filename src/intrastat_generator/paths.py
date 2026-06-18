from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import Any, Dict

from .config import DICT_DIR_NAME, LOG_DIR_NAME, OUTPUT_DIR_NAME
from .naming import now_stamp

def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    module_path = Path(__file__).resolve()
    package_dir = module_path.parent
    for parent in module_path.parents:
        source_package_dir = parent / "src" / "intrastat_generator"
        if source_package_dir.resolve() == package_dir:
            return parent
    return package_dir


def resolve_path(value: str | Path, base_dir: Path) -> Path:
    p = Path(value)
    if p.is_absolute():
        return p
    return base_dir / p


def ensure_dirs(base_dir: Path, config: Dict[str, Any]) -> Dict[str, Path]:
    paths = {
        "base": base_dir,
        "dict": resolve_path(config.get("dict_dir") or DICT_DIR_NAME, base_dir),
        "output": resolve_path(config.get("output_dir") or OUTPUT_DIR_NAME, base_dir),
        "logs": base_dir / LOG_DIR_NAME,
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths


def log_exception(base_dir: Path, exc: BaseException) -> Path:
    log_dir = base_dir / LOG_DIR_NAME
    log_dir.mkdir(parents=True, exist_ok=True)
    p = log_dir / f"blad_{now_stamp()}.log"
    with p.open("w", encoding="utf-8") as f:
        f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    return p

