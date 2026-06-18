from __future__ import annotations

import sys
import traceback
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from .config import DICT_DIR_NAME, LOG_DIR_NAME, OUTPUT_DIR_NAME
from .naming import now_stamp

DICTIONARY_DIR_CANDIDATES = ("Słowniki", "Slowniki", "słowniki", "slowniki")
TARIFF_DIR_CANDIDATES = ("Taryfa", "taryfa")
TARIFF_FILE_CANDIDATES = ("taryfa.txt", "taryfa(1).txt")

def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    module_path = Path(__file__).resolve()
    package_dir = module_path.parent
    for parent in module_path.parents:
        source_package_dir = parent / "src" / "intrastat_generator"
        if source_package_dir.resolve() == package_dir:
            return parent
    return package_dir


def resolve_path(value: str | Path, base_dir: Path) -> Path:
    p = Path(value)
    if p.is_absolute():
        return p
    return base_dir / p


def format_config_path(path: Path) -> str:
    return path.as_posix()


def _unique_paths(paths: Iterable[Path]) -> List[Path]:
    unique: Dict[str, Path] = {}
    for path in paths:
        key = str(path.resolve()).lower() if path.exists() else str(path.absolute()).lower()
        unique.setdefault(key, path)
    return list(unique.values())


def _resource_roots(base_dir: Path) -> List[Path]:
    roots = [base_dir]
    bundle_dir = _bundle_dir()
    if bundle_dir:
        roots.append(bundle_dir)
    return _unique_paths(roots)


def _bundle_dir() -> Path | None:
    bundle_dir = getattr(sys, "_MEIPASS", "")
    return Path(bundle_dir) if bundle_dir else None


def directory_contains_dictionaries(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    return any(p.is_file() and p.name.lower().startswith("slownik") for p in path.rglob("*.xml"))


def _directory_contains_tariff(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    names = {name.lower() for name in TARIFF_FILE_CANDIDATES}
    return any(p.is_file() and p.name.lower() in names for p in path.rglob("*.txt"))


def _copy_missing_tree(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for source_path in source.rglob("*"):
        if not source_path.is_file():
            continue
        relative = source_path.relative_to(source)
        target_path = target / relative
        if target_path.exists():
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


def _materialize_bundled_folder(
    base_dir: Path,
    folder_names: Sequence[str],
    contains_files: Any,
) -> None:
    bundle_dir = _bundle_dir()
    if bundle_dir is None:
        return
    if any(contains_files(base_dir / name) for name in folder_names):
        return
    for name in folder_names:
        source = bundle_dir / name
        if contains_files(source):
            _copy_missing_tree(source, base_dir / source.name)
            return


def materialize_bundled_resources(base_dir: Path) -> None:
    _materialize_bundled_folder(base_dir, DICTIONARY_DIR_CANDIDATES, directory_contains_dictionaries)
    _materialize_bundled_folder(base_dir, TARIFF_DIR_CANDIDATES, _directory_contains_tariff)


def _dictionary_candidates(base_dir: Path, configured: str | Path, roots: Sequence[Path]) -> List[Path]:
    candidates: List[Path] = []
    configured_text = str(configured or "").strip().strip('"')
    if configured_text:
        configured_path = resolve_path(configured_text, base_dir)
        candidates.append(configured_path)
        for name in DICTIONARY_DIR_CANDIDATES:
            candidates.append(configured_path / name)
    for root in roots:
        for name in DICTIONARY_DIR_CANDIDATES:
            candidates.append(root / name)
    return _unique_paths(candidates)


def select_dictionary_dir(base_dir: Path, configured: str | Path = DICT_DIR_NAME) -> Path:
    roots = _resource_roots(base_dir)
    candidates = _dictionary_candidates(base_dir, configured, roots)
    for candidate in candidates:
        if directory_contains_dictionaries(candidate):
            return candidate
    return resolve_path(configured or DICT_DIR_NAME, base_dir)


def _tariff_candidates(base_dir: Path, configured: str | Path, roots: Sequence[Path]) -> List[Path]:
    candidates: List[Path] = []
    configured_text = str(configured or "").strip().strip('"')
    if configured_text:
        candidates.append(resolve_path(configured_text, base_dir))
    for root in roots:
        for name in TARIFF_FILE_CANDIDATES:
            candidates.append(root / name)
        for folder in TARIFF_DIR_CANDIDATES:
            for name in TARIFF_FILE_CANDIDATES:
                candidates.append(root / folder / name)
    return _unique_paths(candidates)


def select_tariff_path(base_dir: Path, configured: str | Path = "") -> Path | None:
    for candidate in _tariff_candidates(base_dir, configured, _resource_roots(base_dir)):
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def ensure_dirs(base_dir: Path, config: Dict[str, Any]) -> Dict[str, Path]:
    materialize_bundled_resources(base_dir)
    dict_dir = select_dictionary_dir(base_dir, config.get("dict_dir") or DICT_DIR_NAME)
    config["dict_dir"] = format_config_path(dict_dir)
    paths = {
        "base": base_dir,
        "dict": dict_dir,
        "output": resolve_path(config.get("output_dir") or OUTPUT_DIR_NAME, base_dir),
        "logs": base_dir / LOG_DIR_NAME,
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths


def log_exception(base_dir: Path, exc: BaseException) -> Path:
    log_dir = base_dir / LOG_DIR_NAME
    log_dir.mkdir(parents=True, exist_ok=True)
    p = log_dir / f"blad_{now_stamp()}.log"
    with p.open("w", encoding="utf-8") as f:
        f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    return p

