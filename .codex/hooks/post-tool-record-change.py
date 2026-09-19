#!/usr/bin/env python3
"""Append lightweight audit hints for files changed by Codex apply_patch."""
from __future__ import annotations
import datetime as dt, json, re, subprocess, sys
from pathlib import Path

def root_for(cwd: Path) -> Path:
    try:
        s=subprocess.check_output(["git","-C",str(cwd),"rev-parse","--show-toplevel"], text=True, stderr=subprocess.DEVNULL).strip(); return Path(s).resolve()
    except Exception: return cwd.resolve()
def paths(command):
    out=[]
    for line in command.splitlines():
        m=re.match(r"^\*\*\* (?:Update|Add|Delete) File:\s+(.+)$", line)
        if m and m.group(1).strip() not in out: out.append(m.group(1).strip())
    return out
try: data=json.load(sys.stdin)
except Exception: sys.exit(0)
if data.get('tool_name') != 'apply_patch': sys.exit(0)
cwd=Path(data.get('cwd') or '.').resolve(); root=root_for(cwd)
command=str((data.get('tool_input') or {}).get('command') or '')
log=root/'.codex'/'evidence'/'session-changes.jsonl'; log.parent.mkdir(parents=True, exist_ok=True)
with log.open('a', encoding='utf-8') as fh:
    for raw in paths(command):
        p=Path(raw); p=(root/p) if not p.is_absolute() else p
        rec={"ts":dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00','Z'),"session_id":data.get('session_id'),"turn_id":data.get('turn_id'),"tool":"apply_patch","path":str(p.resolve(strict=False))}
        fh.write(json.dumps(rec, sort_keys=True)+'\n')
sys.exit(0)
