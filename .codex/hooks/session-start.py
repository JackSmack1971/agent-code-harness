#!/usr/bin/env python3
"""Inject compact repository/phase state at Codex SessionStart."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

def run(*args: str) -> str:
    try:
        return subprocess.check_output(args, stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return "UNAVAILABLE"

try:
    payload = json.load(sys.stdin)
except Exception:
    payload = {}
cwd = Path(payload.get("cwd") or ".").resolve()
root_text = run("git", "-C", str(cwd), "rev-parse", "--show-toplevel")
root = Path(root_text).resolve() if root_text != "UNAVAILABLE" else cwd
branch = run("git", "-C", str(root), "branch", "--show-current")
head = run("git", "-C", str(root), "rev-parse", "HEAD")
status = run("git", "-C", str(root), "status", "--porcelain=v1")
phase_file = root / ".codex" / "evidence" / "current-phase.txt"
phase = phase_file.read_text(encoding="utf-8").strip() if phase_file.exists() else "UNSET"
ctx = "\n".join([
    "### Harness Implementation Session",
    f"- project_root: {root}",
    f"- branch: {branch}",
    f"- head: {head}",
    f"- current_phase: {phase}",
    f"- working_tree: {'clean' if not status else 'dirty'}",
    "- authority: Unified Implementation Blueprint + canonical repository contracts",
    "- closure: use .codex/references/release-gatekeeper-contract.md",
    "- control_plane: instructions influence decisions; Codex policy/runtime authorizes effects",
])
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx}}))
