from __future__ import annotations

import sys
import traceback
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from .config import CONFIG_DIR_NAME, DICT_DIR_NAME, LOG_DIR_NAME, OUTPUT_DIR_NAME
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


def _named_child_dir(parent: Path, name: str) -> Path:
    candidate = parent / name
    if not parent.exists() or not parent.is_dir():
        return candidate
    try:
        for child in parent.iterdir():
            if child.is_dir() and child.name.lower() == name.lower():
                return child
    except OSError:
        return candidate
    return candidate


def _path_is_inside(path: Path, parent: Path) -> bool:
    path_abs = path.resolve() if path.exists() else path.absolute()
    parent_abs = parent.resolve() if parent.exists() else parent.absolute()
    try:
        path_abs.relative_to(parent_abs)
        return True
    except ValueError:
        return False


def _resource_roots(base_dir: Path, include_bundle: bool = True) -> List[Path]:
    roots = [base_dir]
    bundle_dir = _bundle_dir()
    if include_bundle and bundle_dir:
        roots.append(bundle_dir)
    return _unique_paths(roots)


def _bundle_dir() -> Path | None:
    bundle_dir = getattr(sys, "_MEIPASS", "")
    return Path(bundle_dir) if bundle_dir else None


def directory_contains_dictionaries(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    return any(p.is_file() and p.name.lower().startswith("slownik") for p in path.rglob("*.xml"))


def directory_contains_tariff(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    names = {name.lower() for name in TARIFF_FILE_CANDIDATES}
    return any(p.is_file() and p.name.lower() in names for p in path.rglob("*.txt"))


def shared_resource_dir(base_dir: Path) -> Path | None:
    for name in DICTIONARY_DIR_CANDIDATES:
        candidate = _named_child_dir(base_dir, name)
        if directory_contains_dictionaries(candidate) and directory_contains_tariff(candidate):
            return candidate
    return None


def select_config_dir(base_dir: Path) -> Path:
    if shared_resource_dir(base_dir) is not None:
        return base_dir / CONFIG_DIR_NAME
    return base_dir


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
    default_target_name: str | None = None,
) -> None:
    bundle_dir = _bundle_dir()
    if bundle_dir is None:
        return
    sources = [bundle_dir / name for name in folder_names if contains_files(bundle_dir / name)]
    if not sources:
        return
    existing_targets = []
    for name in folder_names:
        target = _named_child_dir(base_dir, name)
        if target.is_dir():
            existing_targets.append(target)
    target = next((path for path in existing_targets if contains_files(path)), None)
    if target is None and existing_targets:
        target = existing_targets[0]
    if target is None:
        target = base_dir / (default_target_name or sources[0].name)
    for source in sources:
        _copy_missing_tree(source, target)


def materialize_bundled_resources(base_dir: Path) -> None:
    if shared_resource_dir(base_dir) is not None:
        return
    _materialize_bundled_folder(base_dir, DICTIONARY_DIR_CANDIDATES, directory_contains_dictionaries, DICT_DIR_NAME)
    _materialize_bundled_folder(base_dir, TARIFF_DIR_CANDIDATES, directory_contains_tariff)


def _dictionary_candidates(base_dir: Path, configured: str | Path, roots: Sequence[Path]) -> List[Path]:
    candidates: List[Path] = []
    configured_text = str(configured or "").strip().strip('"')
    if configured_text:
        configured_path = resolve_path(configured_text, base_dir)
        candidates.append(configured_path)
        for name in DICTIONARY_DIR_CANDIDATES:
            candidates.append(_named_child_dir(configured_path, name))
    for root in roots:
        for name in DICTIONARY_DIR_CANDIDATES:
            candidates.append(_named_child_dir(root, name))
    return _unique_paths(candidates)


def select_dictionary_dir(base_dir: Path, configured: str | Path = DICT_DIR_NAME, include_bundle: bool = True) -> Path:
    roots = _resource_roots(base_dir, include_bundle)
    candidates = _dictionary_candidates(base_dir, configured, roots)
    for candidate in candidates:
        if directory_contains_dictionaries(candidate):
            return candidate
    fallback = resolve_path(configured or DICT_DIR_NAME, base_dir)
    if fallback.is_absolute() and not _path_is_inside(fallback, base_dir):
        return base_dir / DICT_DIR_NAME
    return fallback


def _tariff_candidates(base_dir: Path, configured: str | Path, roots: Sequence[Path]) -> List[Path]:
    candidates: List[Path] = []
    configured_text = str(configured or "").strip().strip('"')
    if configured_text:
        candidates.append(resolve_path(configured_text, base_dir))
    shared_dir = shared_resource_dir(base_dir)
    if shared_dir is not None:
        for name in TARIFF_FILE_CANDIDATES:
            candidates.append(shared_dir / name)
    for root in roots:
        for name in TARIFF_FILE_CANDIDATES:
            candidates.append(root / name)
        for folder in DICTIONARY_DIR_CANDIDATES:
            folder_path = _named_child_dir(root, folder)
            for name in TARIFF_FILE_CANDIDATES:
                candidates.append(folder_path / name)
        for folder in TARIFF_DIR_CANDIDATES:
            folder_path = _named_child_dir(root, folder)
            for name in TARIFF_FILE_CANDIDATES:
                candidates.append(folder_path / name)
    return _unique_paths(candidates)


def select_tariff_path(base_dir: Path, configured: str | Path = "", include_bundle: bool = True) -> Path | None:
    for candidate in _tariff_candidates(base_dir, configured, _resource_roots(base_dir, include_bundle)):
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def ensure_dirs(base_dir: Path, config: Dict[str, Any], config_dir: Path | None = None) -> Dict[str, Path]:
    config_dir = config_dir or select_config_dir(base_dir)
    dict_dir = select_dictionary_dir(base_dir, config.get("dict_dir") or DICT_DIR_NAME, include_bundle=False)
    if not directory_contains_dictionaries(dict_dir):
        _materialize_bundled_folder(base_dir, DICTIONARY_DIR_CANDIDATES, directory_contains_dictionaries, DICT_DIR_NAME)
        dict_dir = select_dictionary_dir(base_dir, config.get("dict_dir") or DICT_DIR_NAME, include_bundle=False)
    if select_tariff_path(base_dir, config.get("tariff_path", ""), include_bundle=False) is None:
        _materialize_bundled_folder(base_dir, TARIFF_DIR_CANDIDATES, directory_contains_tariff)
    config["dict_dir"] = format_config_path(dict_dir)
    paths = {
        "base": base_dir,
        "config": config_dir,
        "dict": dict_dir,
        "output": resolve_path(config.get("output_dir") or OUTPUT_DIR_NAME, base_dir),
        "logs": config_dir / LOG_DIR_NAME,
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths


def log_exception(base_dir: Path, exc: BaseException) -> Path:
    log_dir = select_config_dir(base_dir) / LOG_DIR_NAME
    log_dir.mkdir(parents=True, exist_ok=True)
    p = log_dir / f"blad_{now_stamp()}.log"
    with p.open("w", encoding="utf-8") as f:
        f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    return p

