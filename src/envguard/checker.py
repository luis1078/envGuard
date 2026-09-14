"""Diff a .env file against its .env.example contract."""

from __future__ import annotations

from dataclasses import dataclass, field

from .parser import EnvVar, as_dict

# Values that mean "nobody has filled this in yet" - if .env still has one
# of these (or matches .env.example's own placeholder value verbatim), it's
# flagged as unfilled rather than a real secret. Empty string is handled
# separately in `_looks_like_placeholder` - it's only a placeholder when
# .env.example itself expects a non-empty value.
_PLACEHOLDER_WORDS = {
    "changeme",
    "change_me",
    "change-me",
    "todo",
    "fixme",
    "replace_me",
    "replaceme",
    "your_key_here",
    "your-key-here",
    "example",
    "sample",
    "fake",
    "dummy",
    "placeholder",
    "xxx",
    "xxxx",
    "none",
    "null",
}


@dataclass
class CheckResult:
    missing: list[str] = field(default_factory=list)  # in .env.example, absent from .env
    unfilled: list[str] = field(default_factory=list)  # present but still placeholder-looking
    undocumented: list[str] = field(default_factory=list)  # in .env, absent from .env.example

    @property
    def ok(self) -> bool:
        """True if there's nothing that would break the app at startup.

        `undocumented` is informational only (drift, not breakage) and does
        not affect this - see docstring on `check()`.
        """
        return not self.missing and not self.unfilled


def _looks_like_placeholder(value: str, example_value: str) -> bool:
    normalized = value.strip().strip("'\"").lower()
    if not normalized:
        # Empty is only a placeholder if the example expected something -
        # an empty default in .env.example means blank is the intended value.
        return bool(example_value.strip())
    if normalized in _PLACEHOLDER_WORDS:
        return True
    if normalized.startswith("<") and normalized.endswith(">"):
        return True
    # Copied the example line verbatim without filling it in - only counts
    # if the example's own value is non-empty (an empty example means the
    # var is meant to default to empty, e.g. optional feature flags).
    return bool(example_value) and value == example_value


def check(env_vars: list[EnvVar], example_vars: list[EnvVar]) -> CheckResult:
    """Compare a .env file's contents against a .env.example contract.

    - `missing`: keys declared in .env.example but absent from .env entirely.
    - `unfilled`: keys present in .env but still empty or placeholder-looking.
    - `undocumented`: keys in .env not declared in .env.example - not an
      error (nothing breaks), just drift worth a human glancing at.
    """
    env_map = as_dict(env_vars)
    example_map = as_dict(example_vars)

    result = CheckResult()
    for key, example_value in example_map.items():
        if key not in env_map:
            result.missing.append(key)
        elif _looks_like_placeholder(env_map[key], example_value):
            result.unfilled.append(key)

    for key in env_map:
        if key not in example_map:
            result.undocumented.append(key)

    result.missing.sort()
    result.unfilled.sort()
    result.undocumented.sort()
    return result
