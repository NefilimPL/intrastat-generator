from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .cn import CnResolver
from .config import CONFIG_FILE, DEFAULT_CONFIG, DICT_DIR_NAME, OUTPUT_DIR_NAME, ROUTE_COSTS_FILE, STATUS_MISSING, STATUS_UNCERTAIN, load_json, save_json
from .dictionaries import DictionaryLoader
from .models import DictionaryData
from .naming import build_xlsx_filename
from .parser import IntrastatXmlParser
from .paths import ensure_dirs, get_app_dir, resolve_path
from .tariff import TariffLoader
from .text import norm_text, safe_float
from .transport import RouteCostManager
from .workbook import WorkbookBuilder

class GeneratorService:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or get_app_dir()
        self.config_path = self.base_dir / CONFIG_FILE
        self.config = load_json(self.config_path, DEFAULT_CONFIG)
        ensure_dirs(self.base_dir, self.config)

    def save_config(self) -> None:
        save_json(self.config_path, self.config)

    def route_costs_path(self) -> Path:
        return resolve_path(self.config.get("transport_costs_file", ROUTE_COSTS_FILE), self.base_dir)

    def load_route_cost_config(self) -> Dict[str, Any]:
        manager = RouteCostManager(self.route_costs_path())
        cfg = manager.load()
        cfg["origin_voivodeship"] = self.config.get("origin_voivodeship", cfg.get("origin_voivodeship", "podkarpackie"))
        cfg["allocation_basis"] = self.config.get("transport_allocation_basis", cfg.get("allocation_basis", "mass_net"))
        manager.save(cfg)
        return cfg

    def save_route_cost_config(self, route_config: Dict[str, Any]) -> None:
        manager = RouteCostManager(self.route_costs_path())
        manager.save(route_config)
        self.config["origin_voivodeship"] = route_config.get("origin_voivodeship", self.config.get("origin_voivodeship", "podkarpackie"))
        self.config["transport_allocation_basis"] = route_config.get("allocation_basis", self.config.get("transport_allocation_basis", "invoice_value"))
        self.config["transport_use_invoice_cap"] = bool(route_config.get("use_invoice_cap", self.config.get("transport_use_invoice_cap", True)))
        self.config["transport_max_share_pct"] = safe_float(route_config.get("max_transport_share_pct", self.config.get("transport_max_share_pct", 8.0)), 8.0)
        self.save_config()

    def guess_tariff_path(self) -> str:
        configured = norm_text(self.config.get("tariff_path", ""))
        if configured and Path(configured).exists():
            return configured
        for name in ["taryfa.txt", "taryfa(1).txt"]:
            p = self.base_dir / name
            if p.exists():
                self.config["tariff_path"] = str(p)
                self.save_config()
                return str(p)
        return configured

    def available_tariff_years(self, tariff_path: Path) -> List[str]:
        return TariffLoader(tariff_path).available_years()

    def tariff_year_options(self, tariff_path: Path) -> List[Tuple[str, str]]:
        years = self.available_tariff_years(tariff_path)
        if not years:
            return []
        current = years[0]
        return [(f"{year}-Obecny" if year == current else year, year) for year in years]

    def resolve_tariff_year(self, tariff_path: Path) -> str:
        years = self.available_tariff_years(tariff_path)
        if not years:
            return ""
        configured = norm_text(self.config.get("tariff_year", ""))
        return configured if configured in years else years[0]

    def tariff_year_config_value(self, tariff_path: Path, selected_year: str) -> str:
        years = self.available_tariff_years(tariff_path)
        selected = norm_text(selected_year)
        if not years or selected not in years or selected == years[0]:
            return ""
        return selected

    def load_current_dicts(self) -> Dict[str, DictionaryData]:
        paths = ensure_dirs(self.base_dir, self.config)
        return DictionaryLoader(self.base_dir, paths["dict"]).load()

    def dict_codes_for_gui(self, code: str) -> List[str]:
        try:
            dicts = self.load_current_dicts()
            d = dicts.get(code)
            return [""] + (d.codes() if d else [])
        except Exception:
            return [""]

    def generate(self, input_xml: Path, tariff_path: Path, progress: Optional[Callable[[int, str], None]] = None) -> Tuple[Path, Dict[str, Any]]:
        t0 = time.perf_counter()
        if progress:
            progress(3, "Sprawdzanie plików...")
        if not input_xml.exists():
            raise FileNotFoundError(f"Nie istnieje plik XML: {input_xml}")
        if not tariff_path.exists():
            raise FileNotFoundError(f"Nie istnieje plik taryfy: {tariff_path}")

        configured_tariff_year = norm_text(self.config.get("tariff_year", ""))
        effective_tariff_year = self.resolve_tariff_year(tariff_path)
        self.config["tariff_path"] = str(tariff_path)
        self.config["tariff_year"] = self.tariff_year_config_value(tariff_path, configured_tariff_year)
        self.save_config()
        run_config = self.config.copy()
        run_config["tariff_year"] = effective_tariff_year
        paths = ensure_dirs(self.base_dir, self.config)

        if progress:
            progress(10, "Wczytywanie słowników XML...")
        dicts = DictionaryLoader(self.base_dir, paths["dict"]).load()
        if not dicts:
            raise RuntimeError(f"Nie znaleziono słowników XML. Włóż pliki slownik*.xml do: {paths['dict']}")

        if progress:
            progress(20, "Wczytywanie taryfy CN...")
        tariff_entries = TariffLoader(tariff_path, year=effective_tariff_year).load()
        if not tariff_entries:
            if effective_tariff_year:
                raise RuntimeError(f"Nie udało się wczytać kodów CN z rocznika taryfy {effective_tariff_year}.")
            raise RuntimeError("Nie udało się wczytać kodów CN z taryfa.txt")

        if progress:
            progress(32, "Wczytywanie deklaracji XML...")
        parser = IntrastatXmlParser(input_xml, run_config, dicts)
        items = parser.parse()
        if not items:
            raise RuntimeError("Nie znaleziono żadnych pozycji <Towar> w XML.")

        if progress:
            progress(38, "Wczytywanie tabeli kosztów transportu...")
        route_config = self.load_route_cost_config()

        if progress:
            progress(40, "Dobieranie kodów CN...")
        resolver = CnResolver(
            tariff_entries=tariff_entries,
            confident_threshold=float(run_config.get("cn_confident_threshold", 90.0)),
            uncertain_threshold=float(run_config.get("cn_uncertain_threshold", 80.0)),
        )
        builder = WorkbookBuilder(dicts, tariff_entries, resolver, run_config, route_config=route_config)

        declaration_no = parser.declaration_attrs.get("NrWlasny", "INTRASTAT") or "INTRASTAT"
        month = parser.declaration_attrs.get("Miesiac", "")
        year = parser.declaration_attrs.get("Rok", "")
        output_filename = build_xlsx_filename(declaration_no, year, month)
        xlsx_path = paths["output"] / output_filename

        builder.build(items, parser.declaration_attrs, xlsx_path, progress)
        elapsed = time.perf_counter() - t0
        xlsx_path = max(paths["output"].glob(f"{xlsx_path.stem}*.xlsx"), key=lambda p: p.stat().st_mtime)
        summary = {
            "items_count": len(items),
            "dicts_count": len(dicts),
            "dict_codes": sorted(dicts.keys()),
            "tariff_entries_count": len(tariff_entries),
            "tariff_year": effective_tariff_year,
            "elapsed_seconds": elapsed,
            "warnings_count": len(builder.warnings),
            "missing_cn_count": sum(1 for d in builder.decisions if d.get("Status") == STATUS_MISSING),
            "uncertain_cn_count": sum(1 for d in builder.decisions if d.get("Status") == STATUS_UNCERTAIN),
            "output_dir": str(paths["output"]),
            "statistical_value_mode": run_config.get("statistical_value_mode", ""),
            "origin_voivodeship": route_config.get("origin_voivodeship", ""),
            "transport_allocation_basis": route_config.get("allocation_basis", ""),
        }
        if progress:
            progress(100, f"Gotowe. Czas: {elapsed:.2f} s")
        return xlsx_path, summary


