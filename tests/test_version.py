from intrastat_generator.version import DEFAULT_VERSION, resolve_version


def test_resolve_version_prefers_explicit_build_env():
    env = {"INTRASTAT_GENERATOR_VERSION": "v3.4.0", "GITHUB_REF_NAME": "v3.3.0"}
    assert resolve_version(env) == "v3.4.0"


def test_resolve_version_uses_github_tag_ref():
    env = {"GITHUB_REF_NAME": "v3.4.0"}
    assert resolve_version(env) == "v3.4.0"


def test_resolve_version_ignores_non_tag_ref():
    env = {"GITHUB_REF_NAME": "dev"}
    assert resolve_version(env) == DEFAULT_VERSION


def test_resolve_version_uses_default_without_env():
    assert resolve_version({}) == DEFAULT_VERSION
