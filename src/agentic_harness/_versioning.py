"""Minimal dotted-version parsing/comparison, no external dependency.

Only tolerates the shapes actually emitted by `python --version` and system
`git --version` (including Git for Windows' `2.45.1.windows.1` suffix).
Not a general PEP 440/semver implementation.
"""

from __future__ import annotations

import re

_NUMERIC = re.compile(r"\d+")


def parse_numeric_prefix(text: str, components: int = 3) -> tuple[int, ...]:
    numbers = [int(n) for n in _NUMERIC.findall(text)]
    numbers = numbers[:components]
    while len(numbers) < components:
        numbers.append(0)
    return tuple(numbers)


def at_least(actual: str, minimum: str, components: int = 3) -> bool:
    return parse_numeric_prefix(actual, components) >= parse_numeric_prefix(minimum, components)


def below(actual: str, ceiling_exclusive: str, components: int = 3) -> bool:
    return parse_numeric_prefix(actual, components) < parse_numeric_prefix(ceiling_exclusive, components)
