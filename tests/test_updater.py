from __future__ import annotations

import json
from pathlib import Path
import urllib.error
import urllib.request

from intrastat_generator.project import PROJECT


class FakeResponse:
    def __init__(self, payload: bytes, headers: dict[str, str] | None = None):
        self.payload = payload
        self.headers = headers or {}
        self._offset = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            if self._offset:
                return b""
            self._offset = len(self.payload)
            return self.payload
        if self._offset >= len(self.payload):
            return b""
        chunk = self.payload[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk


def test_parse_version_tuple_ignores_prefix_and_branch_suffix():
    from intrastat_generator.updater import parse_version_tuple

    assert parse_version_tuple("v0.0.6-Main") == (0, 0, 6)
    assert parse_version_tuple("0.0.5-dev") == (0, 0, 5)


def test_parse_version_tuple_returns_none_for_uncomparable_text():
    from intrastat_generator.updater import parse_version_tuple

    assert parse_version_tuple("feature-build") is None


def test_is_newer_version_detects_newer_release():
    from intrastat_generator.updater import is_newer_version

    assert is_newer_version("v0.0.5-dev", "v0.0.6") is True
    assert is_newer_version("v0.0.6-Main", "v0.0.6") is False
    assert is_newer_version("0.0.0-dev", "v0.0.1") is True
    assert is_newer_version("feature-build", "v0.0.1") is False


def test_select_windows_exe_asset_prefers_release_exe():
    from intrastat_generator.updater import GitHubAsset, select_windows_exe_asset

    asset = select_windows_exe_asset(
        [
            GitHubAsset("notes.txt", "https://example.test/notes", 10),
            GitHubAsset("Intrastat-Generator_v0.0.6_Windows_x64.exe", "https://example.test/app.exe", 20),
        ]
    )

    assert asset is not None
    assert asset.name == "Intrastat-Generator_v0.0.6_Windows_x64.exe"


def test_repository_404_is_private_or_unavailable():
    from intrastat_generator.updater import GitHubReleaseClient, RepositoryVisibility

    def opener(_request: urllib.request.Request, timeout: int = 0):
        raise urllib.error.HTTPError("https://api.github.test", 404, "Not Found", {}, None)

    client = GitHubReleaseClient(PROJECT, opener=opener)

    assert client.fetch_repository_visibility() == RepositoryVisibility.PRIVATE_OR_UNAVAILABLE


def test_repository_403_is_private_or_unavailable():
    from intrastat_generator.updater import GitHubReleaseClient, RepositoryVisibility

    def opener(_request: urllib.request.Request, timeout: int = 0):
        raise urllib.error.HTTPError("https://api.github.test", 403, "Forbidden", {}, None)

    client = GitHubReleaseClient(PROJECT, opener=opener)

    assert client.fetch_repository_visibility() == RepositoryVisibility.PRIVATE_OR_UNAVAILABLE


def test_repository_network_failure_is_unavailable():
    from intrastat_generator.updater import GitHubReleaseClient, RepositoryVisibility

    def opener(_request: urllib.request.Request, timeout: int = 0):
        raise urllib.error.URLError("offline")

    client = GitHubReleaseClient(PROJECT, opener=opener)

    assert client.fetch_repository_visibility() == RepositoryVisibility.UNAVAILABLE


def test_latest_update_retries_transient_repository_visibility_failure():
    from intrastat_generator.updater import GitHubReleaseClient, UpdateStatus

    release_payload = {
        "tag_name": "v0.0.6",
        "html_url": "https://github.com/NefilimPL/intrastat-generator/releases/tag/v0.0.6",
        "assets": [
            {
                "name": "Intrastat-Generator_v0.0.6_Windows_x64.exe",
                "browser_download_url": "https://example.test/app.exe",
                "size": 123,
            }
        ],
    }
    calls: dict[str, int] = {}

    def opener(request: urllib.request.Request, timeout: int = 0):
        url = request.full_url
        calls[url] = calls.get(url, 0) + 1
        if url.endswith("/releases/latest"):
            return FakeResponse(json.dumps(release_payload).encode("utf-8"))
        if calls[url] == 1:
            raise urllib.error.URLError("timed out")
        return FakeResponse(json.dumps({"private": False}).encode("utf-8"))

    client = GitHubReleaseClient(PROJECT, opener=opener)

    result = client.check_for_update("v0.0.5-dev")

    assert result.status == UpdateStatus.UPDATE_AVAILABLE
    assert calls[client.repository_api_url] == 2


def test_latest_update_retries_transient_latest_release_failure():
    from intrastat_generator.updater import GitHubReleaseClient, UpdateStatus

    release_payload = {
        "tag_name": "v0.0.6",
        "html_url": "https://github.com/NefilimPL/intrastat-generator/releases/tag/v0.0.6",
        "assets": [
            {
                "name": "Intrastat-Generator_v0.0.6_Windows_x64.exe",
                "browser_download_url": "https://example.test/app.exe",
                "size": 123,
            }
        ],
    }
    calls: dict[str, int] = {}

    def opener(request: urllib.request.Request, timeout: int = 0):
        url = request.full_url
        calls[url] = calls.get(url, 0) + 1
        if url.endswith("/releases/latest") and calls[url] == 1:
            raise urllib.error.URLError("timed out")
        if url.endswith("/releases/latest"):
            return FakeResponse(json.dumps(release_payload).encode("utf-8"))
        return FakeResponse(json.dumps({"private": False}).encode("utf-8"))

    client = GitHubReleaseClient(PROJECT, opener=opener)

    result = client.check_for_update("v0.0.5-dev")

    assert result.status == UpdateStatus.UPDATE_AVAILABLE
    assert calls[client.latest_release_api_url] == 2


def test_latest_update_detects_newer_public_release():
    from intrastat_generator.updater import GitHubReleaseClient, UpdateStatus

    payloads = [
        {"private": False},
        {
            "tag_name": "v0.0.6",
            "html_url": "https://github.com/NefilimPL/intrastat-generator/releases/tag/v0.0.6",
            "assets": [
                {
                    "name": "Intrastat-Generator_v0.0.6_Windows_x64.exe",
                    "browser_download_url": "https://example.test/app.exe",
                    "size": 123,
                }
            ],
        },
    ]

    def opener(_request: urllib.request.Request, timeout: int = 0):
        return FakeResponse(json.dumps(payloads.pop(0)).encode("utf-8"))

    client = GitHubReleaseClient(PROJECT, opener=opener)

    result = client.check_for_update("v0.0.5-dev")

    assert result.status == UpdateStatus.UPDATE_AVAILABLE
    assert result.latest_version == "v0.0.6"
    assert result.release_url == "https://github.com/NefilimPL/intrastat-generator/releases/tag/v0.0.6"
    assert result.asset is not None
    assert result.asset.size == 123


def test_latest_update_ignores_same_version_release():
    from intrastat_generator.updater import GitHubReleaseClient, UpdateStatus

    payloads = [
        {"private": False},
        {
            "tag_name": "v0.0.6",
            "html_url": "https://github.com/NefilimPL/intrastat-generator/releases/tag/v0.0.6",
            "assets": [],
        },
    ]

    def opener(_request: urllib.request.Request, timeout: int = 0):
        return FakeResponse(json.dumps(payloads.pop(0)).encode("utf-8"))

    client = GitHubReleaseClient(PROJECT, opener=opener)

    result = client.check_for_update("v0.0.6-Main")

    assert result.status == UpdateStatus.NO_UPDATE
    assert result.latest_version == "v0.0.6"


def test_download_asset_writes_unique_exe(tmp_path: Path):
    from intrastat_generator.updater import GitHubReleaseClient

    progress: list[tuple[int, int]] = []

    def opener(_request: urllib.request.Request, timeout: int = 0):
        return FakeResponse(b"exe-data", {"Content-Length": "8"})

    client = GitHubReleaseClient(PROJECT, opener=opener)
    asset = client.asset_from_json(
        {
            "name": "Intrastat-Generator_v0.0.6_Windows_x64.exe",
            "browser_download_url": "https://example.test/app.exe",
            "size": 8,
        }
    )

    target = client.download_asset(asset, tmp_path, progress=lambda received, total: progress.append((received, total)))

    assert target.name == "Intrastat-Generator_v0.0.6_Windows_x64.exe"
    assert target.read_bytes() == b"exe-data"
    assert progress[-1] == (8, 8)
    assert not (tmp_path / f"{target.name}.part").exists()
