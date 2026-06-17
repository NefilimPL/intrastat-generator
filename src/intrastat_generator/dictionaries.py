from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional

from .models import DictionaryData
from .text import norm_text, strip_ns

class DictionaryLoader:
    def __init__(self, base_dir: Path, dict_dir: Path):
        self.base_dir = base_dir
        self.dict_dir = dict_dir

    def discover_paths(self) -> List[Path]:
        found: Dict[str, Path] = {}
        for folder in [self.dict_dir, self.base_dir]:
            if not folder.exists():
                continue
            for p in folder.glob("*.xml"):
                if p.name.lower().startswith("slownik"):
                    found[str(p.resolve()).lower()] = p
        return sorted(found.values(), key=lambda p: p.name.lower())

    def load(self) -> Dict[str, DictionaryData]:
        latest: Dict[str, DictionaryData] = {}
        for path in self.discover_paths():
            data = self._parse_one(path)
            if not data:
                continue
            old = latest.get(data.code)
            if old is None or (data.date or "0000-00-00") >= (old.date or "0000-00-00"):
                latest[data.code] = data
        return latest

    def _parse_one(self, path: Path) -> Optional[DictionaryData]:
        try:
            root = ET.parse(path).getroot()
        except Exception:
            return None
        if strip_ns(root.tag) != "Slownik":
            return None
        code = norm_text(root.attrib.get("Kod", ""))
        name = norm_text(root.attrib.get("Nazwa", "") or root.attrib.get("NazwaEN", ""))
        date = norm_text(root.attrib.get("DataEdycji", ""))
        rows: List[Dict[str, str]] = []
        for pos in root.iter():
            if strip_ns(pos.tag) != "Pozycja":
                continue
            rows.append({
                "Kod": norm_text(pos.attrib.get("Kod", "")),
                "Opis": norm_text(pos.attrib.get("Opis", "")),
                "OpisEN": norm_text(pos.attrib.get("OpisEN", "")),
                "WaznyOd": norm_text(pos.attrib.get("WaznyOd", "")),
                "WaznyDo": norm_text(pos.attrib.get("WaznyDo", "")),
            })
        return DictionaryData(code=code, name=name, date=date, path=path, rows=rows)


