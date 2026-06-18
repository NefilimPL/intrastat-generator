from intrastat_generator.version import DEFAULT_VERSION, resolve_version


def test_resolve_version_prefers_explicit_build_env():
    env = {"INTRASTAT_GENERATOR_VERSION": "v3.4.0", "GITHUB_REF_NAME": "v3.3.0"}
    assert resolve_version(env) == "v3.4.0"


def test_resolve_version_uses_github_tag_ref():
    env = {"GITHUB_REF_NAME": "v3.4.0"}
    assert resolve_version(env) == "v3.4.0"


def test_resolve_version_combines_tag_and_branch():
    env = {"GITHUB_REF_NAME": "v0.0.5", "INTRASTAT_GENERATOR_BRANCH": "dev"}
    assert resolve_version(env) == "v0.0.5-dev"


def test_resolve_version_uses_branch_for_non_tag_build():
    env = {"GITHUB_REF_NAME": "feature-x", "INTRASTAT_GENERATOR_BRANCH": "feature-x"}
    assert resolve_version(env) == "0.0.0-feature-x"


def test_resolve_version_sanitizes_branch_for_version_string():
    env = {"GITHUB_REF_NAME": "v1.2.3", "INTRASTAT_GENERATOR_BRANCH": "feature/fix paths"}
    assert resolve_version(env) == "v1.2.3-feature-fix-paths"


def test_resolve_version_ignores_non_tag_ref():
    env = {"GITHUB_REF_NAME": "dev"}
    assert resolve_version(env) == DEFAULT_VERSION


def test_resolve_version_uses_default_without_env():
    assert resolve_version({}) == DEFAULT_VERSION
