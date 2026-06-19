from __future__ import annotations

from intrastat_generator.project import PROJECT
from intrastat_generator.updater import GitHubAsset, RepositoryVisibility, UpdateResult, UpdateStatus


def test_project_info_rows_keep_repository_url_clickable_when_repository_unavailable():
    from intrastat_generator.gui import build_project_info_rows

    rows = build_project_info_rows(
        project=PROJECT,
        version="v1.1.1-Main",
        repository_visibility=RepositoryVisibility.UNAVAILABLE,
        update=None,
        downloaded_update_path=None,
    )

    repository_row = next(row for row in rows if row.label == "Repozytorium")

    assert repository_row.value == PROJECT.repository_url
    assert repository_row.url == PROJECT.repository_url


def test_project_info_rows_mark_release_url_clickable_when_known():
    from intrastat_generator.gui import build_project_info_rows

    release_url = "https://github.com/NefilimPL/intrastat-generator/releases/tag/v1.1.2"
    update = UpdateResult(
        status=UpdateStatus.UPDATE_AVAILABLE,
        repository_visibility=RepositoryVisibility.PUBLIC,
        latest_version="v1.1.2",
        release_url=release_url,
        asset=GitHubAsset("Intrastat-Generator_v1.1.2_Windows_x64.exe", "https://example.test/app.exe", 123),
    )

    rows = build_project_info_rows(
        project=PROJECT,
        version="v1.1.1-Main",
        repository_visibility=RepositoryVisibility.PUBLIC,
        update=update,
        downloaded_update_path=None,
    )

    release_row = next(row for row in rows if row.label == "URL release")

    assert release_row.value == release_url
    assert release_row.url == release_url
