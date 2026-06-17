from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Sequence

from .models import DictionaryData, IntrastatItem
from .text import compact_cn, norm_text, safe_int, strip_ns

class IntrastatXmlParser:
    def __init__(self, path: Path, config: Dict[str, Any], dicts: Dict[str, DictionaryData]):
        self.path = path
        self.config = config
        self.dicts = dicts
        self.declaration_attrs: Dict[str, str] = {}

    @staticmethod
    def _get_attr(attrs: Dict[str, str], candidates: Sequence[str], default: str = "") -> str:
        for c in candidates:
            if c in attrs and norm_text(attrs[c]) != "":
                return norm_text(attrs[c])
        low = {k.lower(): v for k, v in attrs.items()}
        for c in candidates:
            v = low.get(c.lower())
            if v is not None and norm_text(v) != "":
                return norm_text(v)
        return default

    def parse(self) -> List[IntrastatItem]:
        root = ET.parse(self.path).getroot()
        declaration = None
        for elem in root.iter():
            if strip_ns(elem.tag) == "Deklaracja":
                declaration = elem
                break
        if declaration is not None:
            self.declaration_attrs = {k: norm_text(v) for k, v in declaration.attrib.items()}

        items: List[IntrastatItem] = []
        for elem in root.iter():
            if strip_ns(elem.tag) != "Towar":
                continue
            attrs = {k: norm_text(v) for k, v in elem.attrib.items()}
            source_cn = compact_cn(self._get_attr(attrs, ["KodTowarowy", "KodCN", "CN", "KodTowaru"]))
            transaction = self._get_attr(attrs, ["RodzajTransakcji", "KodRodzajuTransakcji"], self.config.get("default_transaction_type", ""))
            invoice_value = safe_int(self._get_attr(attrs, ["WartoscFaktury", "WartoscFakturowa", "WartoscFakturyPLN"]))
            stat_value_xml = safe_int(self._get_attr(attrs, ["WartoscStatystyczna", "WartoscStatystycznaPLN"]))
            stat_value = self._statistical_value(stat_value_xml, invoice_value, transaction, source_cn)

            items.append(IntrastatItem(
                poz_id=self._get_attr(attrs, ["PozId", "Lp", "Pozycja"]),
                opis=self._get_attr(attrs, ["OpisTowaru", "Opis", "NazwaTowaru"]),
                country=self._get_attr(attrs, ["KrajPrzeznaczeniaWysylki", "KrajPrzeznaczenia", "KrajWysylki", "KrajWywozu"]),
                delivery_terms=self._get_attr(attrs, ["WarunkiDostawy", "KodWarunkowDostawy"], self.config.get("default_delivery_terms", "")),
                transaction_type=transaction,
                source_cn=source_cn,
                transport_type=self._get_attr(attrs, ["RodzajTransportu", "KodRodzajuTransportu"], self.config.get("default_transport_type", "")),
                origin_country=self._get_attr(attrs, ["KrajPochodzenia", "KodKrajuPochodzenia"]),
                mass_net=safe_int(self._get_attr(attrs, ["MasaNetto", "MasaNettoKg"]), blank_if_missing=False),
                supplementary_qty=safe_int(self._get_attr(attrs, ["IloscJednostekUzupelniajacych", "IloscJmUzupelniajaca", "IloscUzupelniajaca"])),
                invoice_value=invoice_value,
                statistical_value=stat_value,
                vat_id=self._get_attr(attrs, ["IdKontrahenta", "VatKontrahenta", "NumerVatKontrahenta", "NIPKontrahenta"]),
                attrs=attrs,
            ))
        return items

    def _statistical_value(self, xml_value: Any, invoice_value: Any, transaction_type: str, cn: str) -> Any:
        if xml_value != "":
            return xml_value
        mode = self.config.get("statistical_value_mode", "blank")
        if mode == "copy_invoice_always":
            return invoice_value
        if mode == "copy_invoice_when_required":
            required_by_transaction = transaction_type in set(self.dicts.get("191", DictionaryData("", "", "", Path(), [])).codes())
            required_by_cn = cn in set(self.dicts.get("190", DictionaryData("", "", "", Path(), [])).codes())
            if required_by_transaction or required_by_cn:
                return invoice_value
        return ""


