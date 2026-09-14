from envguard.parser import as_dict, parse_env_text


def test_parses_basic_assignments():
    text = "FOO=bar\nBAZ=1\n"
    result = as_dict(parse_env_text(text))
    assert result == {"FOO": "bar", "BAZ": "1"}


def test_skips_blank_lines_and_comments():
    text = "# comment\n\nFOO=bar\n   # indented comment\n"
    result = as_dict(parse_env_text(text))
    assert result == {"FOO": "bar"}


def test_strips_export_prefix():
    result = as_dict(parse_env_text("export FOO=bar\n"))
    assert result == {"FOO": "bar"}


def test_strips_matching_quotes():
    text = 'SINGLE=\'hello world\'\nDOUBLE="hello world"\nMIXED="don\'t"\n'
    result = as_dict(parse_env_text(text))
    assert result == {"SINGLE": "hello world", "DOUBLE": "hello world", "MIXED": "don't"}


def test_strips_trailing_comment_on_unquoted_value():
    result = as_dict(parse_env_text("PORT=5432 # default postgres port\n"))
    assert result == {"PORT": "5432"}


def test_ignores_lines_without_equals():
    result = as_dict(parse_env_text("this is not an assignment\nFOO=bar\n"))
    assert result == {"FOO": "bar"}


def test_ignores_invalid_keys():
    result = as_dict(parse_env_text("1INVALID=bar\nfine-not=baz\nOK=yes\n"))
    assert result == {"OK": "yes"}


def test_last_assignment_wins():
    result = as_dict(parse_env_text("FOO=first\nFOO=second\n"))
    assert result == {"FOO": "second"}


def test_line_numbers_are_tracked():
    variables = parse_env_text("# comment\nFOO=bar\n\nBAZ=qux\n")
    assert [(v.key, v.line_no) for v in variables] == [("FOO", 2), ("BAZ", 4)]
