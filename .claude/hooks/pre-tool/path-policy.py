#!/usr/bin/env python3
"""Protect secrets, Git internals, and closure evidence from accidental direct edits."""
from __future__ import annotations
import json, os, sys
from pathlib import Path

try:
    data = json.load(sys.stdin)
except Exception as exc:
    print(f"path-policy: invalid hook payload: {exc}", file=sys.stderr)
    sys.exit(2)

root = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()
tool = data.get("tool_name", "")
inp = data.get("tool_input") or {}
raw = inp.get("file_path") or inp.get("path") or ""

if not raw:
    sys.exit(0)

target = Path(raw)
if not target.is_absolute():
    target = root / target

try:
    resolved = target.resolve(strict=False)
except Exception:
    resolved = target.absolute()

def deny(reason: str):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"BLOCKED: {reason}"
        }
    }))
    sys.exit(2)

# Must remain inside repo for project-level edits.
try:
    resolved.relative_to(root)
except ValueError:
    deny(f"write target escapes project root: {resolved}")

parts = set(resolved.parts)
name = resolved.name.lower()

if ".git" in parts:
    deny("direct edits to Git internals are prohibited")
if name in {".env", ".env.local", ".env.production", ".env.development"}:
    deny("secret-bearing environment files are protected")
if name.endswith((".pem", ".key", ".p12", ".pfx")):
    deny("credential/private-key material is protected")

# Gatekeeper verdict/evidence is produced by explicit closure tooling, not normal code edits.
evidence_root = root / ".claude" / "evidence"
try:
    rel = resolved.relative_to(evidence_root)
    if rel.parts and rel.parts[0] in {"closures", "gatekeeper"}:
        deny("closure/gatekeeper evidence is immutable during normal editing")
except ValueError:
    pass

sys.exit(0)
