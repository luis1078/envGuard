"""Parsing for .env-style files (KEY=VALUE, one per line)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EnvVar:
    key: str
    value: str
    line_no: int  # 1-indexed, for error messages


def parse_env_text(text: str) -> list[EnvVar]:
    """Parse the contents of a .env-style file.

    Rules (matching common .env conventions, e.g. python-dotenv):
    - Blank lines and lines starting with '#' are ignored.
    - `export KEY=VALUE` is accepted (the `export ` prefix is stripped).
    - Values may be wrapped in single or double quotes; quotes are stripped.
    - A line with no '=' is ignored rather than raising - .env files in the
      wild sometimes have stray comments or shell snippets.
    """
    results: list[EnvVar] = []
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key or not _is_valid_key(key):
            continue
        value = value.strip()
        # Strip a single matching pair of quotes, and drop a trailing
        # inline comment on unquoted values (`KEY=value # comment`).
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        elif "#" in value:
            value = value.split("#", 1)[0].rstrip()
        results.append(EnvVar(key=key, value=value, line_no=line_no))
    return results


def _is_valid_key(key: str) -> bool:
    return all(c.isalnum() or c == "_" for c in key) and not key[0].isdigit()


def parse_env_file(path: Path) -> list[EnvVar]:
    return parse_env_text(path.read_text(encoding="utf-8"))


def as_dict(variables: list[EnvVar]) -> dict[str, str]:
    """Last assignment wins, matching how shells and dotenv loaders behave."""
    return {v.key: v.value for v in variables}
