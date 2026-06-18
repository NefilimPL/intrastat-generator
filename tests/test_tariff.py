from __future__ import annotations

from pathlib import Path

from intrastat_generator.service import GeneratorService
from intrastat_generator.tariff import TariffLoader


def write_tariff(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def test_tariff_loader_detects_years_descending(tmp_path):
    tariff = tmp_path / "taryfa.txt"
    write_tariff(
        tariff,
        """
TARYFA 2025
    9401 10 00 - Seats 2025
TARYFA 2026
    9401 10 00 - Seats 2026
TARYFA 2024
    9401 10 00 - Seats 2024
""",
    )

    assert TariffLoader(tariff).available_years() == ["2026", "2025", "2024"]


def test_tariff_loader_loads_only_selected_year_section(tmp_path):
    tariff = tmp_path / "taryfa.txt"
    write_tariff(
        tariff,
        """
TARYFA 2026
    9401 10 00 - Seats current
TARYFA 2025
    9401 10 00 - Seats previous
    9403 20 00 - Metal furniture previous
TARYFA 2024
    9401 10 00 - Seats old
""",
    )

    entries = TariffLoader(tariff, year="2025").load()

    assert [entry.code for entry in entries] == ["94011000", "94032000"]
    assert {entry.year for entry in entries} == {"2025"}
    assert entries[0].description == "Seats previous"


def test_tariff_loader_without_year_headers_loads_entire_file(tmp_path):
    tariff = tmp_path / "taryfa.txt"
    write_tariff(
        tariff,
        """
MEBLE
    9401 10 00 - Seats
    9403 20 00 - Metal furniture
""",
    )

    entries = TariffLoader(tariff, year="2026").load()

    assert [entry.code for entry in entries] == ["94011000", "94032000"]
    assert {entry.year for entry in entries} == {""}


def test_service_formats_tariff_year_options_with_current_suffix(tmp_path):
    tariff = tmp_path / "taryfa.txt"
    write_tariff(
        tariff,
        """
TARYFA 2026
    9401 10 00 - Seats current
TARYFA 2025
    9401 10 00 - Seats previous
""",
    )
    service = GeneratorService(tmp_path)

    assert service.tariff_year_options(tariff) == [("2026-Obecny", "2026"), ("2025", "2025")]


def test_service_selects_highest_tariff_year_by_default(tmp_path):
    tariff = tmp_path / "taryfa.txt"
    write_tariff(
        tariff,
        """
TARYFA 2024
    9401 10 00 - Seats old
TARYFA 2026
    9401 10 00 - Seats current
""",
    )
    service = GeneratorService(tmp_path)
    service.config["tariff_year"] = ""

    assert service.resolve_tariff_year(tariff) == "2026"


def test_service_keeps_saved_tariff_year_when_available(tmp_path):
    tariff = tmp_path / "taryfa.txt"
    write_tariff(
        tariff,
        """
TARYFA 2026
    9401 10 00 - Seats current
TARYFA 2025
    9401 10 00 - Seats previous
""",
    )
    service = GeneratorService(tmp_path)
    service.config["tariff_year"] = "2025"

    assert service.resolve_tariff_year(tariff) == "2025"


def test_service_saves_empty_config_value_for_current_tariff_year(tmp_path):
    tariff = tmp_path / "taryfa.txt"
    write_tariff(
        tariff,
        """
TARYFA 2026
    9401 10 00 - Seats current
TARYFA 2025
    9401 10 00 - Seats previous
""",
    )
    service = GeneratorService(tmp_path)

    assert service.tariff_year_config_value(tariff, "2026") == ""
    assert service.tariff_year_config_value(tariff, "2025") == "2025"
