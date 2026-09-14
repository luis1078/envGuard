from envguard.checker import check
from envguard.parser import parse_env_text


def test_ok_when_env_matches_example():
    example = parse_env_text("ANTHROPIC_API_KEY=\nGITHUB_TOKEN=\n")
    env = parse_env_text("ANTHROPIC_API_KEY=sk-ant-real-value\nGITHUB_TOKEN=ghp_realvalue\n")
    result = check(env, example)
    assert result.ok
    assert result.missing == []
    assert result.unfilled == []


def test_detects_missing_key():
    example = parse_env_text("ANTHROPIC_API_KEY=\nGITHUB_TOKEN=\n")
    env = parse_env_text("ANTHROPIC_API_KEY=sk-ant-real-value\n")
    result = check(env, example)
    assert result.missing == ["GITHUB_TOKEN"]
    assert not result.ok


def test_detects_unfilled_placeholder_word():
    example = parse_env_text("API_KEY=\n")
    env = parse_env_text("API_KEY=changeme\n")
    result = check(env, example)
    assert result.unfilled == ["API_KEY"]
    assert not result.ok


def test_detects_value_copied_verbatim_from_example():
    example = parse_env_text("DB_HOST=your-db-host-here\n")
    env = parse_env_text("DB_HOST=your-db-host-here\n")
    result = check(env, example)
    assert result.unfilled == ["DB_HOST"]


def test_empty_example_default_is_not_flagged_as_unfilled():
    # An optional flag that defaults to empty in .env.example shouldn't be
    # flagged just because the user also left it empty.
    example = parse_env_text("FEATURE_FLAG_X=\n")
    env = parse_env_text("FEATURE_FLAG_X=\n")
    result = check(env, example)
    assert result.unfilled == []


def test_undocumented_vars_are_reported_separately_and_dont_fail():
    example = parse_env_text("FOO=\n")
    env = parse_env_text("FOO=bar\nLEGACY_VAR=old\n")
    result = check(env, example)
    assert result.undocumented == ["LEGACY_VAR"]
    assert result.ok


def test_angle_bracket_placeholder_is_flagged():
    example = parse_env_text("REGION=\n")
    env = parse_env_text("REGION=<your-region>\n")
    result = check(env, example)
    assert result.unfilled == ["REGION"]
