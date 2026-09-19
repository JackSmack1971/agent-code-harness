#!/usr/bin/env python3
"""Inject compact repository/phase state at session start."""
from __future__ import annotations
import json
import os
import subprocess
from pathlib import Path

def run(*args: str) -> str:
    try:
        return subprocess.check_output(args, stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return "UNAVAILABLE"

root = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()
branch = run("git", "-C", str(root), "branch", "--show-current")
head = run("git", "-C", str(root), "rev-parse", "HEAD")
status = run("git", "-C", str(root), "status", "--porcelain=v1")
phase_file = root / ".claude" / "evidence" / "current-phase.txt"
phase = phase_file.read_text(encoding="utf-8").strip() if phase_file.exists() else "UNSET"

ctx = "\n".join([
    "### Harness Implementation Session",
    f"- project_root: {root}",
    f"- branch: {branch}",
    f"- head: {head}",
    f"- current_phase: {phase}",
    f"- working_tree: {'clean' if not status else 'dirty'}",
    "- authority: Unified Implementation Blueprint + canonical repository contracts",
    "- closure: use .claude/references/release-gatekeeper-contract.md",
])

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": ctx,
    }
}))
