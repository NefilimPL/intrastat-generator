from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import app_name
from .paths import log_exception
from .service import GeneratorService
from .version import get_version

def main() -> int:
    parser = argparse.ArgumentParser(description=app_name(get_version()))
    parser.add_argument("--input", help="Ścieżka do XML deklaracji")
    parser.add_argument("--tariff", help="Ścieżka do taryfa.txt")
    parser.add_argument("--dict-dir", help="Folder ze słownikami XML slownik*.xml")
    parser.add_argument("--output-dir", help="Folder wynikowy")
    parser.add_argument("--route-costs", help="Plik JSON z kosztami transportu poza PL")
    parser.add_argument("--stat-mode", choices=["blank", "copy_invoice_when_required", "copy_invoice_always", "subtract_foreign_transport_by_route"], help="Tryb wartości statystycznej")
    parser.add_argument("--origin-voivodeship", help="Województwo startowe transportu")
    parser.add_argument("--allocation-basis", choices=["mass_net", "invoice_value"], help="Podział kosztu transportu na pozycje")
    parser.add_argument("--no-gui", action="store_true", help="Uruchom bez GUI")
    args = parser.parse_args()

    service = GeneratorService()
    if args.dict_dir:
        service.config["dict_dir"] = args.dict_dir
    if args.output_dir:
        service.config["output_dir"] = args.output_dir
    if args.route_costs:
        service.config["transport_costs_file"] = args.route_costs
    if args.stat_mode:
        service.config["statistical_value_mode"] = args.stat_mode
    if args.origin_voivodeship:
        service.config["origin_voivodeship"] = args.origin_voivodeship.strip().lower()
    if args.allocation_basis:
        service.config["transport_allocation_basis"] = args.allocation_basis
    if args.tariff:
        service.config["tariff_path"] = args.tariff
    service.save_config()

    if args.no_gui:
        if not args.input:
            print("Brak --input", file=sys.stderr)
            return 2
        tariff = Path(args.tariff or service.guess_tariff_path())

        def progress(percent: int, msg: str) -> None:
            print(f"{percent:3d}% {msg}")

        try:
            xlsx, summary = service.generate(Path(args.input), tariff, progress=progress)
        except Exception as exc:
            log_path = log_exception(service.base_dir, exc)
            print(f"Błąd: {exc}\nLog: {log_path}", file=sys.stderr)
            return 1
        print("\nGotowe:")
        print(f"XLSX: {xlsx}")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    from .gui import App

    app = App()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
