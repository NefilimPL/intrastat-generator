from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import re
import urllib.error
import urllib.request

from .naming import make_unique_path
from .project import ProjectMetadata

GITHUB_API_VERSION = "2022-11-28"
DEFAULT_TIMEOUT_SECONDS = 12
DOWNLOAD_CHUNK_SIZE = 1024 * 128


class RepositoryVisibility(Enum):
    UNKNOWN = "unknown"
    PUBLIC = "public"
    PRIVATE_OR_UNAVAILABLE = "private_or_unavailable"
    UNAVAILABLE = "unavailable"


class UpdateStatus(Enum):
    REPOSITORY_PRIVATE_OR_UNAVAILABLE = "repository_private_or_unavailable"
    REPOSITORY_UNAVAILABLE = "repository_unavailable"
    NO_RELEASE = "no_release"
    NO_UPDATE = "no_update"
    NO_EXE_ASSET = "no_exe_asset"
    UPDATE_AVAILABLE = "update_available"
    ERROR = "error"


@dataclass(frozen=True)
class GitHubAsset:
    name: str
    download_url: str
    size: int


@dataclass(frozen=True)
class UpdateResult:
    status: UpdateStatus
    repository_visibility: RepositoryVisibility
    latest_version: str = ""
    release_url: str = ""
    asset: GitHubAsset | None = None
    message: str = ""


Opener = Callable[..., object]
ProgressCallback = Callable[[int, int], None]


def parse_version_tuple(value: str) -> tuple[int, ...] | None:
    match = re.search(r"v?(\d+(?:\.\d+){1,3})", str(value or ""))
    if not match:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def is_newer_version(current: str, latest: str) -> bool:
    current_tuple = parse_version_tuple(current)
    latest_tuple = parse_version_tuple(latest)
    if current_tuple is None or latest_tuple is None:
        return False
    width = max(len(current_tuple), len(latest_tuple))
    padded_current = current_tuple + (0,) * (width - len(current_tuple))
    padded_latest = latest_tuple + (0,) * (width - len(latest_tuple))
    return padded_latest > padded_current


def select_windows_exe_asset(assets: list[GitHubAsset]) -> GitHubAsset | None:
    for asset in assets:
        name = asset.name.lower()
        if name.endswith(".exe") and "windows" in name:
            return asset
    for asset in assets:
        if asset.name.lower().endswith(".exe"):
            return asset
    return None


class GitHubReleaseClient:
    def __init__(
        self,
        project: ProjectMetadata,
        opener: Opener | None = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        api_base_url: str = "https://api.github.com",
    ):
        self.project = project
        self.opener = opener or urllib.request.urlopen
        self.timeout = timeout
        self.api_base_url = api_base_url.rstrip("/")

    @property
    def repository_api_url(self) -> str:
        return f"{self.api_base_url}/repos/{self.project.repository_slug}"

    @property
    def latest_release_api_url(self) -> str:
        return f"{self.repository_api_url}/releases/latest"

    def fetch_repository_visibility(self) -> RepositoryVisibility:
        try:
            payload = self._request_json(self.repository_api_url)
        except urllib.error.HTTPError as exc:
            if exc.code in {403, 404}:
                return RepositoryVisibility.PRIVATE_OR_UNAVAILABLE
            return RepositoryVisibility.UNAVAILABLE
        except (OSError, urllib.error.URLError, TimeoutError):
            return RepositoryVisibility.UNAVAILABLE
        return RepositoryVisibility.PRIVATE_OR_UNAVAILABLE if payload.get("private") else RepositoryVisibility.PUBLIC

    def check_for_update(self, current_version: str) -> UpdateResult:
        visibility = self.fetch_repository_visibility()
        if visibility == RepositoryVisibility.PRIVATE_OR_UNAVAILABLE:
            return UpdateResult(
                status=UpdateStatus.REPOSITORY_PRIVATE_OR_UNAVAILABLE,
                repository_visibility=visibility,
                message="Repozytorium jest prywatne albo niedostepne publicznie.",
            )
        if visibility != RepositoryVisibility.PUBLIC:
            return UpdateResult(
                status=UpdateStatus.REPOSITORY_UNAVAILABLE,
                repository_visibility=visibility,
                message="Nie udalo sie sprawdzic publicznego statusu repozytorium.",
            )

        try:
            payload = self._request_json(self.latest_release_api_url)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return UpdateResult(status=UpdateStatus.NO_RELEASE, repository_visibility=visibility)
            if exc.code in {403, 404}:
                return UpdateResult(
                    status=UpdateStatus.REPOSITORY_PRIVATE_OR_UNAVAILABLE,
                    repository_visibility=RepositoryVisibility.PRIVATE_OR_UNAVAILABLE,
                    message="Release nie jest publicznie dostepny.",
                )
            return UpdateResult(status=UpdateStatus.ERROR, repository_visibility=visibility, message=str(exc))
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            return UpdateResult(status=UpdateStatus.ERROR, repository_visibility=visibility, message=str(exc))

        latest_version = str(payload.get("tag_name", "")).strip()
        release_url = str(payload.get("html_url", "")).strip()
        assets = [asset for item in payload.get("assets", []) if (asset := self.asset_from_json(item)) is not None]
        if not is_newer_version(current_version, latest_version):
            return UpdateResult(
                status=UpdateStatus.NO_UPDATE,
                repository_visibility=visibility,
                latest_version=latest_version,
                release_url=release_url,
            )
        selected = select_windows_exe_asset(assets)
        if selected is None:
            return UpdateResult(
                status=UpdateStatus.NO_EXE_ASSET,
                repository_visibility=visibility,
                latest_version=latest_version,
                release_url=release_url,
                message="Nowszy release nie zawiera pliku EXE dla Windows.",
            )
        return UpdateResult(
            status=UpdateStatus.UPDATE_AVAILABLE,
            repository_visibility=visibility,
            latest_version=latest_version,
            release_url=release_url,
            asset=selected,
        )

    def asset_from_json(self, item: object) -> GitHubAsset | None:
        if not isinstance(item, dict):
            return None
        name = str(item.get("name", "")).strip()
        download_url = str(item.get("browser_download_url", "") or item.get("download_url", "")).strip()
        if not name or not download_url:
            return None
        try:
            size = int(item.get("size", 0) or 0)
        except (TypeError, ValueError):
            size = 0
        return GitHubAsset(name=name, download_url=download_url, size=max(0, size))

    def download_asset(
        self,
        asset: GitHubAsset,
        target_dir: Path,
        progress: ProgressCallback | None = None,
    ) -> Path:
        target_dir.mkdir(parents=True, exist_ok=True)
        target = make_unique_path(target_dir / Path(asset.name).name)
        part = target.with_name(f"{target.name}.part")
        if part.exists():
            part.unlink()

        request = self._request(asset.download_url, accept="application/octet-stream")
        received = 0
        total = asset.size
        try:
            with self.opener(request, timeout=self.timeout) as response:  # type: ignore[attr-defined]
                header_total = self._content_length(response)
                if header_total > 0:
                    total = header_total
                with part.open("wb") as handle:
                    while True:
                        chunk = response.read(DOWNLOAD_CHUNK_SIZE)
                        if not chunk:
                            break
                        handle.write(chunk)
                        received += len(chunk)
                        if progress:
                            progress(received, total)
            part.replace(target)
            if progress and received == 0:
                progress(0, total)
            return target
        except Exception:
            try:
                if part.exists():
                    part.unlink()
            finally:
                raise

    def _request_json(self, url: str) -> dict[str, object]:
        request = self._request(url, accept="application/vnd.github+json")
        with self.opener(request, timeout=self.timeout) as response:  # type: ignore[attr-defined]
            raw = response.read()
        if not raw:
            return {}
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}

    def _request(self, url: str, accept: str) -> urllib.request.Request:
        return urllib.request.Request(
            url,
            headers={
                "Accept": accept,
                "User-Agent": self.project.name,
                "X-GitHub-Api-Version": GITHUB_API_VERSION,
            },
        )

    def _content_length(self, response: object) -> int:
        headers = getattr(response, "headers", {}) or {}
        try:
            value = headers.get("Content-Length") or headers.get("content-length") or "0"
            return max(0, int(value))
        except (TypeError, ValueError, AttributeError):
            return 0
