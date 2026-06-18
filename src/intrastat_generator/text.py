from __future__ import annotations

import re
import unicodedata
from typing import Any, List, Tuple

from .config import FORBIDDEN_DESC_CHARS

def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def norm_text(value: Any) -> str:
    s = "" if value is None else str(value)
    s = s.replace("\u00a0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def norm_key(value: Any) -> str:
    s = norm_text(value).upper()
    s = s.translate(str.maketrans({"Ł": "L", "ł": "L", "Đ": "D", "đ": "D", "Ø": "O", "ø": "O"}))
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"[^A-Z0-9./()+\- ]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def tokens(value: str) -> set[str]:
    s = norm_key(value)
    return set(re.findall(r"[A-Z0-9]+", s))


def compact_cn(value: Any) -> str:
    digits = re.sub(r"\D", "", "" if value is None else str(value))
    return digits[:8] if len(digits) >= 8 else digits


def clean_description(desc: str) -> Tuple[str, List[str]]:
    warnings: List[str] = []
    s = norm_text(desc)
    for ch in FORBIDDEN_DESC_CHARS:
        if ch in s:
            s = s.replace(ch, " ")
            warnings.append(f"Usunięto niedozwolony znak {ch!r} z opisu")
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > 255:
        s = s[:255]
        warnings.append("Opis ucięty do 255 znaków")
    return s, warnings


def safe_int(value: Any, blank_if_missing: bool = True) -> Any:
    s = norm_text(value)
    if s == "":
        return "" if blank_if_missing else 0
    s = s.replace(" ", "").replace(",", ".")
    try:
        return int(round(float(s)))
    except Exception:
        return "" if blank_if_missing else 0



def safe_float(value: Any, default: float = 0.0) -> float:
    s = norm_text(value).replace(" ", "").replace(",", ".")
    if s == "":
        return default
    try:
        return float(s)
    except Exception:
        return default


def yes_no(value: Any) -> str:
    return "TAK" if bool(value) else "NIE"


def parse_yes_no(value: Any) -> bool:
    s = norm_text(value).upper()
    return s in {"TAK", "T", "TRUE", "1", "YES", "Y"}


