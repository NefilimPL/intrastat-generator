from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

from .models import TariffEntry
from .text import compact_cn

class TariffLoader:
    CODE_RE = re.compile(r"^\s*((?:\d{4})(?:\s+\d{2}){1,2})\s*-\s*(.+?)\s*$")
    YEAR_RE = re.compile(r"^\s*TARYFA\s+(\d{4})\s*$")

    def __init__(self, tariff_path: Path, year: str = ""):
        self.tariff_path = tariff_path
        self.year = str(year or "").strip()

    def available_years(self) -> List[str]:
        years = set()
        with self.tariff_path.open("r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                match = self.YEAR_RE.match(raw.strip())
                if match:
                    years.add(match.group(1))
        return sorted(years, reverse=True)

    def load(self) -> List[TariffEntry]:
        entries: List[TariffEntry] = []
        context: List[Tuple[int, str]] = []
        has_year_headers = bool(self.available_years())
        current_year = ""
        with self.tariff_path.open("r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                line = raw.rstrip("\n\r")
                if not line.strip():
                    continue
                indent = len(line) - len(line.lstrip("\t "))
                stripped = line.strip()
                year_match = self.YEAR_RE.match(stripped)
                if year_match:
                    current_year = year_match.group(1)
                    context.clear()
                    continue
                if has_year_headers and self.year and current_year != self.year:
                    continue
                match = self.CODE_RE.match(line)
                if match:
                    spaced = re.sub(r"\s+", " ", match.group(1).strip())
                    code = compact_cn(spaced)
                    desc = re.sub(r"\s*\[[^\]]*\]\s*$", "", match.group(2).strip())
                    if len(code) == 8:
                        path_text = " > ".join([c[1] for c in context[-7:]] + [desc])
                        entries.append(TariffEntry(code=code, spaced_code=spaced, description=desc, path_text=path_text, year=current_year if has_year_headers else ""))
                    self._push_context(context, indent, f"{spaced} {desc}")
                else:
                    if len(stripped) <= 150 and not stripped.startswith("TARYFA"):
                        self._push_context(context, indent, stripped)
        # Deduplikacja po kodzie i ścieżce, bo w niektórych plikach taryfa powtarza sekcje.
        unique: Dict[str, TariffEntry] = {}
        for e in entries:
            if e.code not in unique or len(e.path_text) > len(unique[e.code].path_text):
                unique[e.code] = e
        return sorted(unique.values(), key=lambda x: x.code)

    @staticmethod
    def _push_context(context: List[Tuple[int, str]], indent: int, text: str) -> None:
        while context and context[-1][0] >= indent:
            context.pop()
        context.append((indent, text))


