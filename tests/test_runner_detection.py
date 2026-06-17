from __future__ import annotations

import importlib.util
from pathlib import Path


def load_runner_check_module():
    script_path = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "check_self_hosted_runner.py"
    spec = importlib.util.spec_from_file_location("check_self_hosted_runner", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_online_idle_windows_x64_runner_is_available():
    module = load_runner_check_module()
    runner = {
        "status": "online",
        "busy": False,
        "labels": [{"name": "self-hosted"}, {"name": "Windows"}, {"name": "X64"}],
    }

    assert module.runner_is_available(runner)


def test_busy_runner_is_not_available():
    module = load_runner_check_module()
    runner = {
        "status": "online",
        "busy": True,
        "labels": [{"name": "self-hosted"}, {"name": "Windows"}, {"name": "X64"}],
    }

    assert not module.runner_is_available(runner)


def test_payload_reports_available_when_any_matching_runner_is_idle():
    module = load_runner_check_module()
    payload = {
        "runners": [
            {
                "status": "online",
                "busy": True,
                "labels": [{"name": "self-hosted"}, {"name": "Windows"}, {"name": "X64"}],
            },
            {
                "status": "online",
                "busy": False,
                "labels": [{"name": "self-hosted"}, {"name": "Windows"}, {"name": "X64"}],
            },
        ]
    }

    assert module.runners_available(payload)


def test_permission_denied_maps_to_unknown_availability():
    module = load_runner_check_module()

    result = module.outputs_for_error(403)

    assert result["available"] == "unknown"
    assert result["checked"] == "false"
    assert result["reason"] == "permission_denied"
