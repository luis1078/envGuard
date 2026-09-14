"""Small subprocess wrappers around git - only what the scanner/hook need."""

from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(RuntimeError):
    pass


def _run(args: list[str], cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitError("git executable not found on PATH") from exc
    if result.returncode != 0:
        raise GitError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def repo_root(cwd: Path | None = None) -> Path:
    return Path(_run(["rev-parse", "--show-toplevel"], cwd=cwd).strip())


def staged_files(cwd: Path | None = None) -> list[str]:
    """Paths staged for commit (added/copied/modified), relative to repo root."""
    output = _run(["diff", "--cached", "--name-only", "--diff-filter=ACM"], cwd=cwd)
    return [line for line in output.splitlines() if line]


def staged_content(path: str, cwd: Path | None = None) -> str:
    """The exact content of `path` as it is staged (the index), not the
    working tree - so edits made after `git add` are correctly ignored,
    matching what will actually be committed."""
    return _run(["show", f":{path}"], cwd=cwd)


def staged_file_contents(cwd: Path | None = None) -> dict[str, str]:
    """{path: staged content} for every staged file, skipping ones that
    fail to read as text (binaries) or were deleted-then-restaged oddly."""
    contents: dict[str, str] = {}
    for path in staged_files(cwd=cwd):
        try:
            contents[path] = staged_content(path, cwd=cwd)
        except GitError:
            continue
    return contents
