from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github" / "scripts" / "embed_build_info.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("embed_build_info", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_info_text_writes_python_literals():
    module = load_script_module()

    text = module.build_info_text("v1.0.7-main", "main")

    assert "BUILD_VERSION = 'v1.0.7-main'" in text
    assert "BUILD_BRANCH = 'main'" in text


def test_build_info_text_escapes_quotes_for_valid_python():
    module = load_script_module()

    text = module.build_info_text("v1.0.7-'main", "feature/quote'")

    compile(text, str(SCRIPT), "exec")
