from envguard.scanner import scan_text


def test_flags_aws_access_key():
    findings = scan_text("AWS_ACCESS_KEY_ID=AKIAABCDEFGHIJKLMNOP\n")
    assert len(findings) == 1
    assert findings[0].rule == "AWS Access Key ID"


def test_flags_github_token():
    findings = scan_text("token = ghp_" + "a" * 36)
    assert any(f.rule == "GitHub token" for f in findings)


def test_flags_anthropic_key():
    findings = scan_text("ANTHROPIC_API_KEY=sk-ant-" + "x" * 30)
    assert any(f.rule == "Anthropic API key" for f in findings)


def test_flags_private_key_block():
    findings = scan_text("-----BEGIN RSA PRIVATE KEY-----\nMIIB...\n-----END RSA PRIVATE KEY-----\n")
    assert any(f.rule == "Private key block" for f in findings)


def test_generic_assignment_rule_catches_unknown_secret_shape():
    # Deliberately NOT shaped like a real Stripe webhook secret (no "whsec_"
    # prefix) so this fixture isn't flagged by GitHub secret scanning - it
    # only needs to exercise the generic fallback rule, not any
    # brand-specific pattern.
    findings = scan_text("STRIPE_WEBHOOK_SECRET=not-a-real-secret-fixture-9f8e7d6c5b4a\n")
    assert any(f.rule == "Possible credential in assignment" for f in findings)


def test_does_not_flag_placeholder_values():
    findings = scan_text(
        "API_KEY=changeme\n"
        "DB_PASSWORD=\n"
        "SECRET_TOKEN=your_key_here\n"
        "SESSION_SECRET=<fill-me-in>\n"
    )
    assert findings == []


def test_does_not_flag_short_values():
    findings = scan_text("API_KEY=short\n")
    assert findings == []


def test_does_not_flag_shell_variable_reference():
    findings = scan_text("API_KEY=$SECRET_FROM_CI\n")
    assert findings == []


def test_ignore_marker_suppresses_line():
    findings = scan_text("ANTHROPIC_API_KEY=sk-ant-" + "x" * 30 + "  # envguard:ignore\n")
    assert findings == []


def test_masks_the_reported_value():
    findings = scan_text("AWS_ACCESS_KEY_ID=AKIAABCDEFGHIJKLMNOP\n")
    masked = findings[0].masked_value
    assert masked.startswith("AKIA")
    assert masked.endswith("MNOP")
    assert "*" in masked
    assert "ABCDEFGHIJKL" not in masked


def test_known_pattern_does_not_also_trigger_generic_rule():
    # A line matching a named pattern (key contains "KEY") should be
    # reported once, not once per matching rule.
    findings = scan_text("ANTHROPIC_API_KEY=sk-ant-" + "x" * 30 + "\n")
    assert len(findings) == 1


def test_line_numbers_are_reported():
    findings = scan_text("FOO=bar\nAWS_ACCESS_KEY_ID=AKIAABCDEFGHIJKLMNOP\n")
    assert findings[0].line_no == 2
