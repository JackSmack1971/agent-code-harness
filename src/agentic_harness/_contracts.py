"""Read-only accessors for the repository's canonical `contracts/` sources.

Nothing in this module executes at import time. Every function performs a
filesystem read only when explicitly called by a command (e.g. `harness
doctor`), never as a side effect of importing `agentic_harness`.
"""

from __future__ import annotations

import importlib.resources
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_BUNDLED_SUBDIR = "_bundled_contracts"
_MARKER = "research_register.yaml"


def find_contracts_root() -> Path | None:
    """Locate the authoritative `contracts/` directory.

    Prefers a copy bundled into the installed package (built wheel); falls
    back to walking up from this file to find a development checkout's
    top-level `contracts/` directory. Returns None if neither is found,
    which callers MUST treat as a blocked/unsupported capability rather
    than guessing contract content.
    """
    try:
        bundled = importlib.resources.files("agentic_harness") / _BUNDLED_SUBDIR
        if bundled.is_dir() and (bundled / _MARKER).is_file():
            return Path(str(bundled))
    except (ModuleNotFoundError, FileNotFoundError):
        pass

    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "contracts"
        if (candidate / _MARKER).is_file():
            return candidate
    return None


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


@dataclass(frozen=True)
class ContractSet:
    root: Path
    product_manifest: dict[str, Any]
    research_register: list[dict[str, Any]]


def load_contract_set() -> ContractSet | None:
    root = find_contracts_root()
    if root is None:
        return None
    manifest = load_yaml(root / "product_manifest.yaml")
    register = load_yaml(root / "research_register.yaml")
    return ContractSet(root=root, product_manifest=manifest, research_register=register["records"])


def find_research_record(register: list[dict[str, Any]], research_id: str) -> dict[str, Any] | None:
    for record in register:
        if record["research_id"] == research_id:
            return record
    return None
