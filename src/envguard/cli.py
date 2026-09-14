"""Command-line entry point: `envguard <check|scan|install-hook|uninstall-hook>`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import checker, git_utils, hook, scanner
from .parser import parse_env_file


def _cmd_check(args: argparse.Namespace) -> int:
    env_path = Path(args.env)
    example_path = Path(args.example)

    if not example_path.exists():
        print(f"envguard: {example_path} not found - nothing to check against.", file=sys.stderr)
        return 2
    if not env_path.exists():
        print(f"envguard: {env_path} not found. Copy {example_path} to {env_path} and fill it in.")
        return 1

    result = checker.check(parse_env_file(env_path), parse_env_file(example_path))

    if result.missing:
        print(f"Missing from {env_path} (declared in {example_path}):")
        for key in result.missing:
            print(f"  - {key}")
    if result.unfilled:
        print(f"Still look like placeholders in {env_path}:")
        for key in result.unfilled:
            print(f"  - {key}")
    if result.undocumented and args.show_undocumented:
        print(f"In {env_path} but not documented in {example_path} (informational):")
        for key in result.undocumented:
            print(f"  - {key}")

    if result.ok:
        print(f"envguard: {env_path} satisfies {example_path}.")
        return 0

    print("\nenvguard: environment is not ready - see above.", file=sys.stderr)
    return 1


def _cmd_scan(args: argparse.Namespace) -> int:
    if not args.staged and not args.paths:
        print("envguard: scan needs --staged or at least one path.", file=sys.stderr)
        return 2

    if args.staged:
        try:
            file_contents = git_utils.staged_file_contents()
        except git_utils.GitError as exc:
            print(f"envguard: {exc}", file=sys.stderr)
            return 2
    else:
        file_contents = {}
        for raw_path in args.paths:
            path = Path(raw_path)
            if path.is_dir():
                for sub in path.rglob("*"):
                    if sub.is_file():
                        file_contents[str(sub)] = _read_text_lenient(sub)
            else:
                file_contents[str(path)] = _read_text_lenient(path)

    findings = scanner.scan_files(file_contents)
    if not findings:
        print(f"envguard: no likely secrets found in {len(file_contents)} file(s).")
        return 0

    print(f"envguard: {len(findings)} possible secret(s) found:\n")
    for finding in findings:
        print(f"  {finding}")
    print(
        "\nIf a match is a false positive, add `# envguard:ignore` on that line, "
        "or move the real secret out of the repo (e.g. into your local .env)."
    )
    return 1


def _read_text_lenient(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except (UnicodeDecodeError, OSError):
        return ""


def _cmd_install_hook(args: argparse.Namespace) -> int:
    try:
        root = git_utils.repo_root()
        hook_path = hook.install(root, force=args.force)
    except (git_utils.GitError, hook.HookError) as exc:
        print(f"envguard: {exc}", file=sys.stderr)
        return 1
    print(f"envguard: installed pre-commit hook at {hook_path}")
    return 0


def _cmd_uninstall_hook(args: argparse.Namespace) -> int:
    try:
        root = git_utils.repo_root()
        changed = hook.uninstall(root)
    except (git_utils.GitError, hook.HookError) as exc:
        print(f"envguard: {exc}", file=sys.stderr)
        return 1
    print("envguard: hook removed." if changed else "envguard: no hook was installed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="envguard", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="Compare .env against .env.example")
    p_check.add_argument("--env", default=".env")
    p_check.add_argument("--example", default=".env.example")
    p_check.add_argument(
        "--show-undocumented", action="store_true", help="Also list vars in .env not present in .env.example"
    )
    p_check.set_defaults(func=_cmd_check)

    p_scan = sub.add_parser("scan", help="Scan files (or staged changes) for likely secrets")
    p_scan.add_argument("paths", nargs="*", help="Files or directories to scan")
    p_scan.add_argument(
        "--staged", action="store_true", help="Scan the git index (what `git commit` would commit) instead of paths"
    )
    p_scan.set_defaults(func=_cmd_scan)

    p_install = sub.add_parser("install-hook", help="Install envguard as a git pre-commit hook")
    p_install.add_argument("--force", action="store_true", help="Overwrite an existing pre-commit hook (backed up)")
    p_install.set_defaults(func=_cmd_install_hook)

    p_uninstall = sub.add_parser("uninstall-hook", help="Remove the envguard pre-commit hook")
    p_uninstall.set_defaults(func=_cmd_uninstall_hook)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
