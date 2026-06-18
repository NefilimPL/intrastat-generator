from __future__ import annotations

import os
import re
from collections.abc import Mapping

try:
    from ._build_info import BUILD_VERSION
except Exception:
    BUILD_VERSION = ""

DEFAULT_VERSION = "0.0.0-dev"
VERSION_ENV = "INTRASTAT_GENERATOR_VERSION"
BRANCH_ENV = "INTRASTAT_GENERATOR_BRANCH"


def _safe_version_part(value: str) -> str:
    text = value.strip()
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text


def resolve_version(env: Mapping[str, str] | None = None) -> str:
    use_runtime_environment = env is None
    values = os.environ if use_runtime_environment else env
    explicit = values.get(VERSION_ENV, "").strip()
    if explicit:
        return explicit

    embedded = str(BUILD_VERSION).strip() if use_runtime_environment else ""
    if embedded:
        return embedded

    github_ref = values.get("GITHUB_REF_NAME", "").strip()
    branch = _safe_version_part(values.get(BRANCH_ENV, "").strip())
    if github_ref.startswith("v"):
        return f"{github_ref}-{branch}" if branch else github_ref
    if branch:
        return f"0.0.0-{branch}"
    if github_ref:
        return f"0.0.0-{_safe_version_part(github_ref)}" if _safe_version_part(github_ref) else DEFAULT_VERSION

    return DEFAULT_VERSION


def get_version() -> str:
    return resolve_version()
