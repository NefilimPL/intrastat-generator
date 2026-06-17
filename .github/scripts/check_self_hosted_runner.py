from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REQUIRED_LABELS = {"self-hosted", "windows", "x64"}
API_VERSION = "2022-11-28"


def label_names(runner: dict[str, Any]) -> set[str]:
    labels = runner.get("labels", [])
    if not isinstance(labels, list):
        return set()
    return {
        str(label.get("name", "")).strip().lower()
        for label in labels
        if isinstance(label, dict) and str(label.get("name", "")).strip()
    }


def runner_is_available(runner: dict[str, Any], required_labels: set[str] | None = None) -> bool:
    required = required_labels or REQUIRED_LABELS
    status = str(runner.get("status", "")).strip().lower()
    busy = bool(runner.get("busy", False))
    return status == "online" and not busy and required.issubset(label_names(runner))


def runners_available(payload: dict[str, Any]) -> bool:
    runners = payload.get("runners", [])
    if not isinstance(runners, list):
        return False
    return any(isinstance(runner, dict) and runner_is_available(runner) for runner in runners)


def outputs_for_error(status_code: int | None) -> dict[str, str]:
    if status_code == 403:
        return {
            "available": "unknown",
            "checked": "false",
            "reason": "permission_denied",
        }
    return {
        "available": "unknown",
        "checked": "false",
        "reason": "api_error",
    }


def write_outputs(outputs: dict[str, str]) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        for key, value in outputs.items():
            print(f"{key}={value}")
        return

    with Path(output_path).open("a", encoding="utf-8") as output:
        for key, value in outputs.items():
            output.write(f"{key}={value}\n")


def fetch_runner_payload(repository: str, token: str) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{repository}/actions/runners?per_page=100"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": API_VERSION,
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    token = os.environ.get("RUNNER_CHECK_TOKEN", "").strip() or os.environ.get("GITHUB_TOKEN", "").strip()
    if not repository or not token:
        write_outputs({"available": "unknown", "checked": "false", "reason": "missing_config"})
        print("::warning::Cannot check self-hosted runners because repository or token is missing.")
        return 0

    try:
        payload = fetch_runner_payload(repository, token)
    except urllib.error.HTTPError as exc:
        outputs = outputs_for_error(exc.code)
        write_outputs(outputs)
        if exc.code == 403:
            print(
                "::warning::Cannot list self-hosted runners with the current token. "
                "GitHub requires repository Administration read access for this endpoint. "
                "Set secret RUNNER_CHECK_TOKEN to enable exact fallback detection. "
                "Using self-hosted-first scheduling."
            )
        else:
            print(f"::warning::Runner availability check failed with HTTP {exc.code}; using self-hosted-first scheduling.")
        return 0
    except Exception as exc:
        write_outputs(outputs_for_error(None))
        print(f"::warning::Runner availability check failed: {exc}; using self-hosted-first scheduling.")
        return 0

    available = runners_available(payload)
    write_outputs({
        "available": "true" if available else "false",
        "checked": "true",
        "reason": "matched" if available else "no_idle_matching_runner",
    })
    if available:
        print("Found an online idle self-hosted Windows X64 runner.")
    else:
        print("No online idle self-hosted Windows X64 runner found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
