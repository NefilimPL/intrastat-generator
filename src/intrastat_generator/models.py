from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from .config import STATUS_OK


@dataclass
class DictionaryData:
    code: str
    name: str
    date: str
    path: Path
    rows: List[Dict[str, str]]

    def codes(self) -> List[str]:
        return [r.get("Kod", "") for r in self.rows if r.get("Kod")]


@dataclass
class TariffEntry:
    code: str
    spaced_code: str
    description: str
    path_text: str


@dataclass
class IntrastatItem:
    poz_id: str
    opis: str
    country: str
    delivery_terms: str
    transaction_type: str
    source_cn: str
    transport_type: str
    origin_country: str
    mass_net: Any
    supplementary_qty: Any
    invoice_value: Any
    statistical_value: Any
    vat_id: str
    attrs: Dict[str, str]


@dataclass
class StatValueResult:
    value: Any
    correction: Any
    route_total_cost: Any
    share: Any
    route_name: str
    method: str
    note: str
    status: str = STATUS_OK


@dataclass
class CnDecision:
    code: str
    status: str
    confidence: float
    method: str
    matched_text: str
    note: str


