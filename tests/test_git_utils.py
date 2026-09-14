import subprocess
from pathlib import Path

import pytest

from envguard import git_utils


@pytest.fixture
def repo(tmp_path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    return tmp_path


def test_staged_files_lists_added_file(repo):
    (repo / "a.txt").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "a.txt"], cwd=repo, check=True)

    assert git_utils.staged_files(cwd=repo) == ["a.txt"]


def test_staged_content_reads_index_not_working_tree(repo):
    (repo / "a.txt").write_text("staged version\n", encoding="utf-8")
    subprocess.run(["git", "add", "a.txt"], cwd=repo, check=True)
    # Edit after staging - staged_content should still see the staged version.
    (repo / "a.txt").write_text("edited after staging\n", encoding="utf-8")

    assert git_utils.staged_content("a.txt", cwd=repo) == "staged version\n"


def test_staged_file_contents_skips_unmodified_files(repo):
    (repo / "a.txt").write_text("hello\n", encoding="utf-8")
    (repo / "b.txt").write_text("world\n", encoding="utf-8")
    subprocess.run(["git", "add", "a.txt"], cwd=repo, check=True)

    contents = git_utils.staged_file_contents(cwd=repo)
    assert contents == {"a.txt": "hello\n"}


def test_repo_root_finds_top_level(repo):
    nested = repo / "sub"
    nested.mkdir()
    assert git_utils.repo_root(cwd=nested) == repo.resolve()


def test_non_git_directory_raises(tmp_path):
    with pytest.raises(git_utils.GitError):
        git_utils.repo_root(cwd=tmp_path)
