from __future__ import annotations

from pathlib import Path


def release_workflow_text() -> str:
    return (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")


def job_block(workflow: str, job_name: str, next_job_name: str) -> str:
    start = workflow.index(f"\n  {job_name}:")
    end = workflow.index(f"\n  {next_job_name}:", start)
    return workflow[start:end]


def test_self_hosted_artifact_upload_is_optional():
    workflow = release_workflow_text()
    self_hosted = job_block(workflow, "build-self-hosted", "build-github-hosted")
    upload_step = self_hosted[self_hosted.index("- name: Upload artifact"):]

    assert "continue-on-error: true" in upload_step


def test_release_publish_does_not_require_actions_artifact_download():
    workflow = release_workflow_text()

    assert "actions/download-artifact" not in workflow
