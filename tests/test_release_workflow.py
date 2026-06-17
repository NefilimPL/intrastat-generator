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


def test_release_publish_steps_keep_release_as_draft():
    workflow = release_workflow_text()
    publish_steps = workflow.split("- name: Publish release")[1:]

    assert publish_steps
    for publish_step in publish_steps:
        step_body = publish_step.split("- name: Upload artifact", 1)[0]
        assert "draft: true" in step_body


def test_manual_workflow_accepts_release_tag_input():
    workflow = release_workflow_text()

    assert "release_tag:" in workflow
    assert "required: true" in workflow
    assert "RELEASE_TAG:" in workflow


def test_publish_steps_target_selected_release_tag():
    workflow = release_workflow_text()
    publish_steps = workflow.split("- name: Publish release")[1:]

    assert publish_steps
    for publish_step in publish_steps:
        step_body = publish_step.split("- name: Upload artifact", 1)[0]
        assert "github.event_name == 'workflow_dispatch'" in step_body
        assert "tag_name: ${{ env.RELEASE_TAG }}" in step_body


def test_build_uses_selected_release_tag_for_version_and_exe_name():
    workflow = release_workflow_text()

    assert "INTRASTAT_GENERATOR_VERSION: ${{ env.RELEASE_TAG }}" in workflow
    assert "build_release_exe_name('${{ env.RELEASE_TAG }}')" in workflow
