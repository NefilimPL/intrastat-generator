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
