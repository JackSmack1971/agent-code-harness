#!/usr/bin/env python3
"""Protect sensitive paths for Codex apply_patch edits."""
from __future__ import annotations
import json, re, subprocess, sys
from pathlib import Path

def root_for(cwd: Path) -> Path:
    try:
        s = subprocess.check_output(["git","-C",str(cwd),"rev-parse","--show-toplevel"], text=True, stderr=subprocess.DEVNULL).strip()
        return Path(s).resolve()
    except Exception:
        return cwd.resolve()

def patch_paths(command: str):
    patterns = [r"^\*\*\* (?:Update|Add|Delete) File:\s+(.+)$", r"^\+\+\+\s+(?:b/)?(.+)$"]
    seen=[]
    for line in command.splitlines():
        for rx in patterns:
            m=re.match(rx,line)
            if m:
                p=m.group(1).strip()
                if p != '/dev/null' and p not in seen: seen.append(p)
    return seen

def deny(reason: str):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny",
        "permissionDecisionReason": f"BLOCKED: {reason}"
    }})); sys.exit(0)

try: data=json.load(sys.stdin)
except Exception as exc:
    print(f"path-policy: invalid hook payload: {exc}", file=sys.stderr); sys.exit(2)
if data.get('tool_name') != 'apply_patch': sys.exit(0)
cwd=Path(data.get('cwd') or '.').resolve(); root=root_for(cwd)
command=str((data.get('tool_input') or {}).get('command') or '')
for raw in patch_paths(command):
    target=Path(raw)
    if not target.is_absolute(): target=root/target
    resolved=target.resolve(strict=False)
    try: rel=resolved.relative_to(root)
    except ValueError: deny(f"write target escapes project root: {resolved}")
    parts=set(rel.parts); name=resolved.name.lower()
    if '.git' in parts: deny('direct edits to Git internals are prohibited')
    if name in {'.env','.env.local','.env.production','.env.development'}: deny('secret-bearing environment files are protected')
    if name.endswith(('.pem','.key','.p12','.pfx')): deny('credential/private-key material is protected')
    ev=root/'.codex'/'evidence'
    try:
        erel=resolved.relative_to(ev)
        if erel.parts and erel.parts[0] in {'closures','gatekeeper'}:
            deny('closure/gatekeeper evidence is immutable during normal editing')
    except ValueError: pass
sys.exit(0)
