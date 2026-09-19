#!/usr/bin/env python3
"""Cheap end-of-turn guard against unsupported closure claims.

This does not run the full test suite. It blocks only when the working tree
contains obvious implementation placeholders in changed Python source while
the turn is ending. The release-gatekeeper remains the authoritative phase gate.
"""
from __future__ import annotations
import json, os, re, subprocess, sys
from pathlib import Path

try:
    payload = json.load(sys.stdin)
except Exception:
    payload = {}

if payload.get("stop_hook_active"):
    sys.exit(0)

root = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()

try:
    changed = subprocess.check_output(
        ["git", "-C", str(root), "diff", "--name-only", "--diff-filter=ACMR"],
        text=True,
        stderr=subprocess.DEVNULL,
    ).splitlines()
except Exception:
    sys.exit(0)

patterns = [
    re.compile(r"^\s*pass\s*(#.*)?$", re.M),
    re.compile(r"\bNotImplementedError\b"),
    re.compile(r"\bTODO\b.*\bimplement", re.I),
    re.compile(r"\bPLACEHOLDER\b", re.I),
]

hits = []
for rel in changed:
    p = root / rel
    if p.suffix != ".py" or not p.is_file():
        continue
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        continue
    if any(rx.search(text) for rx in patterns):
        hits.append(rel)

if hits:
    print(json.dumps({
        "decision": "block",
        "reason": (
            "Completion blocked: changed Python files contain implementation "
            f"placeholders requiring review: {', '.join(hits[:12])}. "
            "Do not claim completion until placeholders are justified or removed."
        )
    }))
    sys.exit(2)

sys.exit(0)
