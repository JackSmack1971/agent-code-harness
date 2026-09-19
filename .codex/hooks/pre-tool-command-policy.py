#!/usr/bin/env python3
"""Fail-closed guard for destructive/authority-bypassing Bash calls."""
from __future__ import annotations
import json, re, sys
try:
    data = json.load(sys.stdin)
except Exception as exc:
    print(f"command-policy: invalid hook payload: {exc}", file=sys.stderr)
    sys.exit(2)
cmd = str((data.get("tool_input") or {}).get("command") or "")
BLOCK = [
    (r"(^|\s)sudo(\s|$)", "privilege escalation is not permitted"),
    (r"\brm\s+-[^\n]*r[^\n]*f[^\n]*(/|\~|\*)", "broad destructive deletion is blocked"),
    (r"\bgit\s+push\b[^\n]*--force", "force push is blocked"),
    (r"\bgit\s+clean\b[^\n]*-[^\n]*x", "git clean with ignored-file deletion is blocked"),
    (r"\bgit\s+reset\s+--hard\b", "hard reset requires explicit human handling"),
    (r"\bgit\s+checkout\s+--\s+\.", "bulk checkout discard is blocked"),
    (r"\bgit\s+restore\b[^\n]*--worktree\b[^\n]*\.", "bulk worktree discard is blocked"),
    (r"--dangerously-bypass-approvals-and-sandbox|--yolo", "Codex approval/sandbox bypass is blocked"),
]
for pattern, reason in BLOCK:
    if re.search(pattern, cmd, flags=re.IGNORECASE):
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"BLOCKED: {reason}."
        }}))
        sys.exit(0)
sys.exit(0)
