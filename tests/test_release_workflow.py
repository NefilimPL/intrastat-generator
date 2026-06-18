from __future__ import annotations

from pathlib import Path


def release_workflow_text() -> str:
    return (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")


def job_block(workflow: str, job_name: str, next_job_name: str | None = None) -> str:
    start = workflow.index(f"\n  {job_name}:")
    end = workflow.index(f"\n  {next_job_name}:", start) if next_job_name else len(workflow)
    return workflow[start:end]


def test_self_hosted_artifact_upload_is_optional():
    workflow = release_workflow_text()
    self_hosted = job_block(workflow, "build-self-hosted", "build-github-hosted")
    upload_step = self_hosted[self_hosted.index("- name: Upload artifact"):]

    assert "continue-on-error: true" in upload_step


def test_release_publish_does_not_require_actions_artifact_download():
    workflow = release_workflow_text()

    assert "actions/download-artifact" not in workflow


def test_release_publish_steps_keep_release_as_draft():
    workflow = release_workflow_text()
    publish_steps = workflow.split("- name: Publish release")[1:]

    assert publish_steps
    for publish_step in publish_steps:
        step_body = publish_step.split("- name: Upload artifact", 1)[0]
        assert "draft: true" in step_body


def test_windows_build_jobs_run_tests_before_building_exe():
    workflow = release_workflow_text()

    for job_name in ["build-self-hosted", "build-github-hosted"]:
        block = job_block(workflow, job_name)

        assert "- name: Run tests" in block
        assert block.index("- name: Run tests") < block.index("- name: Build EXE")


def test_windows_build_jobs_compute_tag_branch_version_before_tests():
    workflow = release_workflow_text()

    for job_name in ["build-self-hosted", "build-github-hosted"]:
        block = job_block(workflow, job_name)

        assert "- name: Prepare build version" in block
        assert "fetch-depth: 0" in block
        assert "INTRASTAT_GENERATOR_BRANCH" in block
        assert "INTRASTAT_GENERATOR_VERSION" in block
        assert "github.ref_type" in block
        assert block.index("- name: Prepare build version") < block.index("- name: Run tests")


def test_windows_build_jobs_embed_runtime_build_info_before_tests():
    workflow = release_workflow_text()

    for job_name in ["build-self-hosted", "build-github-hosted"]:
        block = job_block(workflow, job_name)

        assert "- name: Embed runtime build info" in block
        assert ".github/scripts/embed_build_info.py" in block
        assert "src/intrastat_generator/_build_info.py" in block
        assert block.index("- name: Embed runtime build info") < block.index("- name: Run tests")
        assert block.index("- name: Embed runtime build info") < block.index("- name: Build EXE")


def test_windows_build_jobs_add_exe_metadata_and_bundle_resources():
    workflow = release_workflow_text()

    for job_name in ["build-self-hosted", "build-github-hosted"]:
        block = job_block(workflow, job_name)

        assert "- name: Generate EXE metadata" in block
        assert "--version-file" in block
        assert "build/version_info.txt" in block or "build\\version_info.txt" in block
        assert "--add-data" in block
        assert "build/pyinstaller-resources/Slowniki;Slowniki" in block
        assert "build/pyinstaller-resources/Taryfa;Taryfa" in block
        assert "build_release_exe_name('$env:INTRASTAT_GENERATOR_VERSION')" in block


def test_windows_build_jobs_stage_all_resource_files_before_pyinstaller():
    workflow = release_workflow_text()

    for job_name in ["build-self-hosted", "build-github-hosted"]:
        block = job_block(workflow, job_name)
        build_step = block[block.index("- name: Build EXE") :]

        assert "- name: Stage bundled resources" in block
        assert block.index("- name: Stage bundled resources") < block.index("- name: Build EXE")
        assert "build/pyinstaller-resources/Slowniki" in block
        assert "build/pyinstaller-resources/Taryfa" in block
        assert "Copy-Item" in block
        assert "build/pyinstaller-resources/Slowniki;Slowniki" in build_step
        assert "build/pyinstaller-resources/Taryfa;Taryfa" in build_step


def test_windows_exe_metadata_uses_polish_language_and_project_legal_info():
    workflow = release_workflow_text()

    for job_name in ["build-self-hosted", "build-github-hosted"]:
        block = job_block(workflow, job_name)

        assert "'041504B0'" in block
        assert "VarStruct('Translation', [1045, 1200])" in block
        assert "'040904B0'" not in block
        assert "VarStruct('Translation', [1033, 1200])" not in block
        assert "StringStruct('CompanyName', 'NefilimPL and contributors')" in block
        assert "StringStruct('LegalCopyright', 'Copyright (c) 2026 NefilimPL and contributors')" in block
        assert "StringStruct('Comments', 'License: MIT; Authors: NefilimPL and contributors')" in block


def test_version_info_here_strings_remain_inside_yaml_run_blocks():
    lines = release_workflow_text().splitlines()

    for index, line in enumerate(lines):
        if line.strip() != '@"':
            continue
        indent = line[: len(line) - len(line.lstrip())]
        assert lines[index + 1].startswith(indent)
        closing_index = next(i for i in range(index + 1, len(lines)) if lines[i].lstrip().startswith('"@'))
        for body_line in lines[index + 1 : closing_index + 1]:
            assert body_line.startswith(indent)


def test_self_hosted_build_uses_existing_python_instead_of_setup_python():
    workflow = release_workflow_text()
    self_hosted = job_block(workflow, "build-self-hosted", "build-github-hosted")

    assert "actions/setup-python" not in self_hosted
    assert "- name: Select existing Python" in self_hosted
    assert "PYTHON_EXE" in self_hosted
    assert "import sys, tkinter" in self_hosted
    assert "shell: pwsh" not in self_hosted
    assert "shell: powershell" not in self_hosted
    assert "PowerShell edition" in self_hosted


def test_github_hosted_build_uses_node24_compatible_setup_python():
    workflow = release_workflow_text()
    github_hosted = job_block(workflow, "build-github-hosted")

    assert "actions/setup-python@v6" in github_hosted
