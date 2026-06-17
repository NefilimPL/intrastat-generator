from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def safe_filename_part(value: object, fallback: str = "") -> str:
    text = "" if value is None else str(value).strip()
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or fallback


def build_xlsx_filename(
    declaration_no: object,
    year: object,
    month: object,
    timestamp: str | None = None,
) -> str:
    stamp = timestamp or now_stamp()
    declaration = safe_filename_part(declaration_no, "INTRASTAT")
    year_part = safe_filename_part(year)
    month_part = safe_filename_part(month)

    parts = ["INTRASTAT"]
    if declaration and declaration != "INTRASTAT":
        parts.append(declaration)
    if year_part and month_part:
        parts.append(f"{year_part}-{month_part}")
    elif year_part:
        parts.append(year_part)
    elif month_part:
        parts.append(month_part)
    parts.append(safe_filename_part(stamp, "timestamp"))
    return "_".join(parts) + ".xlsx"


def build_release_exe_name(version: str) -> str:
    text = "" if version is None else str(version).strip()
    safe_version = re.sub(r"[^A-Za-z0-9_.-]+", "_", text)
    safe_version = re.sub(r"_+", "_", safe_version).strip("_") or "0.0.0-dev"
    return f"Intrastat-Generator_{safe_version}_Windows_x64.exe"


def make_unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    for index in range(1, 1000):
        candidate = path.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
    return path.with_name(f"{stem}_{now_stamp()}{suffix}")
