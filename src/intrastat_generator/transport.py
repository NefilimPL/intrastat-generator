from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import DEFAULT_ROUTE_COSTS, STATUS_OK, STATUS_UNCERTAIN
from .models import IntrastatItem, StatValueResult
from .text import norm_text, safe_float

class RouteCostManager:
    def __init__(self, path: Path):
        self.path = path

    @staticmethod
    def default_config() -> Dict[str, Any]:
        return json.loads(json.dumps(DEFAULT_ROUTE_COSTS, ensure_ascii=False))

    def load(self) -> Dict[str, Any]:
        cfg = self.default_config()
        if self.path.exists():
            try:
                with self.path.open("r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    cfg.update({k: v for k, v in loaded.items() if k != "routes"})
                    if isinstance(loaded.get("routes"), list):
                        cfg["routes"] = loaded["routes"]
            except Exception:
                pass
        self._normalize(cfg)
        # Jeżeli plik nie istnieje, zapisz tabelę startową obok programu.
        if not self.path.exists():
            self.save(cfg)
        return cfg

    def save(self, cfg: Dict[str, Any]) -> None:
        self._normalize(cfg)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _normalize(cfg: Dict[str, Any]) -> None:
        cfg["origin_voivodeship"] = norm_text(cfg.get("origin_voivodeship") or "podkarpackie").lower()
        cfg["allocation_basis"] = norm_text(cfg.get("allocation_basis") or "invoice_value")
        cfg["use_invoice_cap"] = bool(cfg.get("use_invoice_cap", True))
        cfg["max_transport_share_pct"] = safe_float(cfg.get("max_transport_share_pct", 8.0), 8.0)
        if cfg["allocation_basis"] not in {"mass_net", "invoice_value"}:
            cfg["allocation_basis"] = "mass_net"
        routes = cfg.get("routes")
        if not isinstance(routes, list):
            routes = []
        normalized: List[Dict[str, Any]] = []
        for r in routes:
            if not isinstance(r, dict):
                continue
            country = norm_text(r.get("country", "")).upper()
            if not country:
                continue
            zone = norm_text(r.get("zone", "STANDARD")).upper() or "STANDARD"
            normalized.append({
                "active": bool(r.get("active", True)),
                "country": country,
                "zone": zone,
                "foreign_cost_pln": safe_float(r.get("foreign_cost_pln", 0.0)),
                "truck_count": max(0.0, safe_float(r.get("truck_count", 1.0))),
                "max_correction_pct": safe_float(r.get("max_correction_pct", cfg.get("max_transport_share_pct", 8.0)), safe_float(cfg.get("max_transport_share_pct", 8.0), 8.0)),
                "default": bool(r.get("default", False)),
                "note": norm_text(r.get("note", "")),
            })
        if not normalized:
            normalized = RouteCostManager.default_config()["routes"]
        cfg["routes"] = normalized

    @staticmethod
    def select_route(route_config: Dict[str, Any], country: str) -> Optional[Dict[str, Any]]:
        country = norm_text(country).upper()
        active = [r for r in route_config.get("routes", []) if bool(r.get("active", True)) and norm_text(r.get("country", "")).upper() == country]
        if not active:
            return None
        defaults = [r for r in active if bool(r.get("default", False))]
        return defaults[0] if defaults else active[0]



class StatisticalValueCalculator:
    def __init__(self, config: Dict[str, Any], route_config: Dict[str, Any], declaration_attrs: Dict[str, str]):
        self.config = config
        self.route_config = route_config
        self.declaration_attrs = declaration_attrs
        self.warnings: List[str] = []

    def calculate(self, items: List[IntrastatItem]) -> Dict[int, StatValueResult]:
        mode = self.config.get("statistical_value_mode", "blank")
        if mode != "subtract_foreign_transport_by_route":
            return {
                idx: StatValueResult(item.statistical_value, "", "", "", "", f"tryb: {mode}", "")
                for idx, item in enumerate(items)
            }

        typ = norm_text(self.declaration_attrs.get("Typ", "")).upper()
        if typ and typ != "W":
            self.warnings.append("Tryb odejmowania transportu poza PL jest przygotowany dla wywozu Typ=W. Dla innego typu deklaracji pozostawiono wartości jak z XML/ustawień.")
            return {
                idx: StatValueResult(item.statistical_value, "", "", "", "", "tryb kosztowy nieużyty", "Deklaracja nie wygląda na wywóz Typ=W", STATUS_UNCERTAIN)
                for idx, item in enumerate(items)
            }

        basis = norm_text(self.route_config.get("allocation_basis") or self.config.get("transport_allocation_basis") or "mass_net")
        if basis not in {"mass_net", "invoice_value"}:
            basis = "mass_net"

        selected_routes: Dict[str, Optional[Dict[str, Any]]] = {}
        group_basis: Dict[str, float] = {}
        group_invoice: Dict[str, float] = {}
        for item in items:
            country = norm_text(item.country).upper()
            if country not in selected_routes:
                selected_routes[country] = RouteCostManager.select_route(self.route_config, country)
            r = selected_routes[country]
            if not r:
                continue
            key = self._route_key(r)
            group_basis[key] = group_basis.get(key, 0.0) + self._basis_value(item, basis)
            group_invoice[key] = group_invoice.get(key, 0.0) + max(0.0, safe_float(item.invoice_value, 0.0))

        results: Dict[int, StatValueResult] = {}
        for idx, item in enumerate(items):
            invoice = safe_float(item.invoice_value, 0.0)
            country = norm_text(item.country).upper()
            route = selected_routes.get(country)
            if not route:
                results[idx] = StatValueResult(
                    value=item.statistical_value if item.statistical_value != "" else item.invoice_value,
                    correction="",
                    route_total_cost="",
                    share="",
                    route_name=f"{country}: BRAK",
                    method="brak kosztu trasy - skopiowano fakturę/źródło",
                    note=f"Brak aktywnej trasy kosztowej dla kraju {country}",
                    status=STATUS_UNCERTAIN,
                )
                self.warnings.append(f"Poz {item.poz_id}: brak aktywnej trasy kosztowej dla kraju {country}")
                continue
            key = self._route_key(route)
            total_basis = group_basis.get(key, 0.0)
            own_basis = self._basis_value(item, basis)
            if total_basis <= 0:
                results[idx] = StatValueResult(
                    value=item.statistical_value if item.statistical_value != "" else item.invoice_value,
                    correction="",
                    route_total_cost="",
                    share="",
                    route_name=key,
                    method="brak podstawy podziału - skopiowano fakturę/źródło",
                    note="Suma masy/wartości dla grupy wynosi 0",
                    status=STATUS_UNCERTAIN,
                )
                self.warnings.append(f"Poz {item.poz_id}: brak podstawy podziału kosztu dla trasy {key}")
                continue
            share = own_basis / total_basis
            route_cost_one = safe_float(route.get("foreign_cost_pln", 0.0), 0.0)
            truck_count = max(0.0, safe_float(route.get("truck_count", 1.0), 1.0))
            route_total_raw = route_cost_one * truck_count

            use_cap = bool(self.route_config.get("use_invoice_cap", self.config.get("transport_use_invoice_cap", True)))
            global_cap_pct = safe_float(self.route_config.get("max_transport_share_pct", self.config.get("transport_max_share_pct", 8.0)), 8.0)
            route_cap_pct = safe_float(route.get("max_correction_pct", global_cap_pct), global_cap_pct)
            invoice_group_total = group_invoice.get(key, 0.0)
            route_total = route_total_raw
            capped = False
            if use_cap and route_cap_pct > 0 and invoice_group_total > 0:
                route_cap_value = invoice_group_total * route_cap_pct / 100.0
                if route_total_raw > route_cap_value:
                    route_total = route_cap_value
                    capped = True

            correction = route_total * share
            stat_value = int(round(max(0.0, invoice - correction)))
            correction_rounded = int(round(correction))
            method = f"faktura - koszt poza PL; podział: {'masa netto' if basis == 'mass_net' else 'wartość faktury'}; limit grupy: {route_cap_pct:g}% faktur; woj.: {self.route_config.get('origin_voivodeship', '')}"
            note = norm_text(route.get("note", ""))
            status = STATUS_OK
            if capped:
                note = (note + " | " if note else "") + f"Koszt trasy ograniczony limitem {route_cap_pct:g}% wartości faktur grupy: {route_total_raw:.0f} -> {route_total:.0f} PLN"
            if correction > invoice and invoice > 0:
                status = STATUS_UNCERTAIN
                note = (note + " | " if note else "") + "Korekta większa niż faktura; wynik obcięty do 0"
            results[idx] = StatValueResult(
                value=stat_value,
                correction=correction_rounded,
                route_total_cost=int(round(route_total)),
                share=share,
                route_name=key,
                method=method,
                note=note,
                status=status,
            )
        return results

    @staticmethod
    def _route_key(route: Dict[str, Any]) -> str:
        return f"{norm_text(route.get('country')).upper()}_{norm_text(route.get('zone') or 'STANDARD').upper()}"

    @staticmethod
    def _basis_value(item: IntrastatItem, basis: str) -> float:
        if basis == "invoice_value":
            return max(0.0, safe_float(item.invoice_value, 0.0))
        return max(0.0, safe_float(item.mass_net, 0.0))


