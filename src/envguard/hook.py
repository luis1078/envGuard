"""Install/remove envguard as a git pre-commit hook."""

from __future__ import annotations

from pathlib import Path

_MARKER = "# installed by envguard - https://github.com/ (see envguard hook.py)"

_HOOK_SCRIPT = f"""#!/bin/sh
{_MARKER}
envguard scan --staged
exit $?
"""


class HookError(RuntimeError):
    pass


def _hooks_dir(repo_root: Path) -> Path:
    hooks_dir = repo_root / ".git" / "hooks"
    if not hooks_dir.is_dir():
        raise HookError(f"{repo_root} does not look like a git repository (no .git/hooks)")
    return hooks_dir


def install(repo_root: Path, force: bool = False) -> Path:
    """Write the pre-commit hook. Refuses to clobber an existing hook that
    envguard didn't create, unless force=True (in which case the old hook
    is backed up to pre-commit.bak.envguard)."""
    hook_path = _hooks_dir(repo_root) / "pre-commit"

    if hook_path.exists():
        existing = hook_path.read_text(encoding="utf-8", errors="replace")
        if _MARKER not in existing:
            if not force:
                raise HookError(
                    f"{hook_path} already exists and wasn't created by envguard. "
                    "Re-run with force=True to back it up and overwrite it."
                )
            backup_path = hook_path.with_name("pre-commit.bak.envguard")
            backup_path.write_text(existing, encoding="utf-8")

    hook_path.write_text(_HOOK_SCRIPT, encoding="utf-8")
    hook_path.chmod(0o755)
    return hook_path


def uninstall(repo_root: Path) -> bool:
    """Remove the hook if envguard installed it, restoring a backup if one
    exists. Returns True if anything changed."""
    hook_path = _hooks_dir(repo_root) / "pre-commit"
    if not hook_path.exists():
        return False

    existing = hook_path.read_text(encoding="utf-8", errors="replace")
    if _MARKER not in existing:
        raise HookError(f"{hook_path} was not created by envguard - leaving it alone")

    backup_path = hook_path.with_name("pre-commit.bak.envguard")
    hook_path.unlink()
    if backup_path.exists():
        backup_path.rename(hook_path)
    return True
