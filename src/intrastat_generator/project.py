from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectMetadata:
    name: str
    display_name: str
    description: str
    authors: str
    license: str
    repository_owner: str
    repository_name: str

    @property
    def repository_slug(self) -> str:
        return f"{self.repository_owner}/{self.repository_name}"

    @property
    def repository_url(self) -> str:
        return f"https://github.com/{self.repository_slug}"


PROJECT = ProjectMetadata(
    name="intrastat-generator",
    display_name="Generator INTRASTAT XLSX",
    description="Generator XLSX INTRASTAT",
    authors="NefilimPL and contributors",
    license="MIT",
    repository_owner="NefilimPL",
    repository_name="intrastat-generator",
)
