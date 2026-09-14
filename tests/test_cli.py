from pathlib import Path

from envguard.cli import main


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_check_passes_when_env_is_complete(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / ".env.example", "API_KEY=\n")
    _write(tmp_path / ".env", "API_KEY=real-value\n")

    assert main(["check"]) == 0
    assert "satisfies" in capsys.readouterr().out


def test_check_fails_when_env_missing(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / ".env.example", "API_KEY=\n")

    assert main(["check"]) == 1


def test_check_fails_when_var_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / ".env.example", "API_KEY=\nOTHER=\n")
    _write(tmp_path / ".env", "API_KEY=value\n")

    assert main(["check"]) == 1


def test_check_missing_example_file_is_a_config_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["check"]) == 2


def test_scan_paths_reports_findings(tmp_path, capsys):
    secret_file = tmp_path / "settings.py"
    _write(secret_file, "AWS_ACCESS_KEY_ID = 'AKIAABCDEFGHIJKLMNOP'\n")

    exit_code = main(["scan", str(secret_file)])

    assert exit_code == 1
    assert "AWS Access Key ID" in capsys.readouterr().out


def test_scan_paths_clean_file_passes(tmp_path):
    clean_file = tmp_path / "settings.py"
    _write(clean_file, "DEBUG = True\n")

    assert main(["scan", str(clean_file)]) == 0


def test_scan_without_staged_or_paths_errors(capsys):
    assert main(["scan"]) == 2
    assert "needs --staged or at least one path" in capsys.readouterr().err
