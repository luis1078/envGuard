import subprocess
from pathlib import Path

import pytest

from envguard import hook


def _init_repo(path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    return path


@pytest.fixture
def repo(tmp_path) -> Path:
    return _init_repo(tmp_path)


def test_install_creates_executable_hook(repo):
    hook_path = hook.install(repo)
    assert hook_path == repo / ".git" / "hooks" / "pre-commit"
    content = hook_path.read_text(encoding="utf-8")
    assert "envguard scan --staged" in content


def test_install_refuses_to_clobber_foreign_hook(repo):
    hook_path = repo / ".git" / "hooks" / "pre-commit"
    hook_path.write_text("#!/bin/sh\necho custom hook\n", encoding="utf-8")

    with pytest.raises(hook.HookError):
        hook.install(repo)

    # Original content must be untouched.
    assert "custom hook" in hook_path.read_text(encoding="utf-8")


def test_install_force_backs_up_foreign_hook(repo):
    hook_path = repo / ".git" / "hooks" / "pre-commit"
    hook_path.write_text("#!/bin/sh\necho custom hook\n", encoding="utf-8")

    hook.install(repo, force=True)

    backup_path = hook_path.with_name("pre-commit.bak.envguard")
    assert "custom hook" in backup_path.read_text(encoding="utf-8")
    assert "envguard scan --staged" in hook_path.read_text(encoding="utf-8")


def test_install_is_idempotent_on_its_own_hook(repo):
    hook.install(repo)
    # Re-installing over envguard's own hook should not raise even without force.
    hook.install(repo)


def test_uninstall_removes_hook(repo):
    hook.install(repo)
    changed = hook.uninstall(repo)
    assert changed is True
    assert not (repo / ".git" / "hooks" / "pre-commit").exists()


def test_uninstall_restores_backup(repo):
    hook_path = repo / ".git" / "hooks" / "pre-commit"
    hook_path.write_text("#!/bin/sh\necho custom hook\n", encoding="utf-8")
    hook.install(repo, force=True)

    hook.uninstall(repo)

    assert "custom hook" in hook_path.read_text(encoding="utf-8")


def test_uninstall_refuses_to_remove_foreign_hook(repo):
    hook_path = repo / ".git" / "hooks" / "pre-commit"
    hook_path.write_text("#!/bin/sh\necho custom hook\n", encoding="utf-8")

    with pytest.raises(hook.HookError):
        hook.uninstall(repo)


def test_uninstall_when_nothing_installed_is_a_noop(repo):
    assert hook.uninstall(repo) is False


def test_install_requires_a_git_repo(tmp_path):
    not_a_repo = tmp_path / "plain_dir"
    not_a_repo.mkdir()
    with pytest.raises(hook.HookError):
        hook.install(not_a_repo)
