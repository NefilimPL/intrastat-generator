from __future__ import annotations

import os
from collections.abc import Mapping

DEFAULT_VERSION = "0.0.0-dev"
VERSION_ENV = "INTRASTAT_GENERATOR_VERSION"


def resolve_version(env: Mapping[str, str] | None = None) -> str:
    values = os.environ if env is None else env
    explicit = values.get(VERSION_ENV, "").strip()
    if explicit:
        return explicit

    github_ref = values.get("GITHUB_REF_NAME", "").strip()
    if github_ref.startswith("v"):
        return github_ref

    return DEFAULT_VERSION


def get_version() -> str:
    return resolve_version()
