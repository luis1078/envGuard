"""Regex-based scanner for credentials that shouldn't be committed.

This is deliberately simple (a fixed pattern list + one heuristic for
KEY=<long-looking-secret> assignments) rather than an entropy-scoring
engine - it trades some recall for being easy to read, extend, and trust.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# (name, regex) - regexes are matched with re.search on each line.
# Ordered roughly by specificity; the generic assignment rule runs last.
_KNOWN_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("AWS Access Key ID", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9\-_]{20,}\b")),
    ("OpenAI API key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("Stripe live key", re.compile(r"\bsk_live_[0-9a-zA-Z]{16,}\b")),
    (
        "Private key block",
        re.compile(r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    ),
]

# Matches KEY=value assignments where the key name suggests a secret.
_SECRET_ASSIGNMENT_RE = re.compile(
    r"^[ \t]*(?:export\s+)?"
    r"(?P<key>[A-Za-z_][A-Za-z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|PWD)[A-Za-z0-9_]*)"
    r"\s*=\s*['\"]?(?P<value>[^'\"\s#]{12,})['\"]?",
    re.IGNORECASE,
)

_IGNORE_MARKER = "envguard:ignore"

_LOW_ENTROPY_VALUES = {
    "changeme",
    "change_me",
    "your_key_here",
    "placeholder",
    "example",
    "sample",
    "test",
    "localhost",
}


@dataclass(frozen=True)
class Finding:
    file: str
    line_no: int
    rule: str
    masked_value: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line_no}: [{self.rule}] {self.masked_value}"


def _mask(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


def _generic_assignment_finding(line: str) -> str | None:
    match = _SECRET_ASSIGNMENT_RE.match(line)
    if not match:
        return None
    value = match.group("value").strip("'\"")
    if value.lower() in _LOW_ENTROPY_VALUES:
        return None
    if value.startswith("<") and value.endswith(">"):
        return None
    if value.startswith("$"):  # shell/CI variable reference, not a literal secret
        return None
    return value


def scan_text(text: str, filename: str = "<text>") -> list[Finding]:
    """Scan file contents line by line and return every finding.

    A line containing the `envguard:ignore` marker (as a comment) is
    skipped entirely, mirroring `# noqa` / `# nosec` conventions.
    """
    findings: list[Finding] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if _IGNORE_MARKER in line:
            continue

        matched_known = False
        for rule_name, pattern in _KNOWN_PATTERNS:
            match = pattern.search(line)
            if match:
                findings.append(Finding(filename, line_no, rule_name, _mask(match.group(0))))
                matched_known = True

        if matched_known:
            continue  # avoid double-reporting the same line under the generic rule

        secret_value = _generic_assignment_finding(line)
        if secret_value:
            findings.append(
                Finding(filename, line_no, "Possible credential in assignment", _mask(secret_value))
            )

    return findings


def scan_files(paths: dict[str, str]) -> list[Finding]:
    """Scan a {path: content} mapping (e.g. staged file contents)."""
    findings: list[Finding] = []
    for path, content in paths.items():
        findings.extend(scan_text(content, filename=path))
    return findings
