#!/usr/bin/env python3
"""Append a lightweight audit hint for files changed during the Claude session."""
from __future__ import annotations
import datetime as dt
import json, os, sys
from pathlib import Path

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

root = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()
inp = data.get("tool_input") or {}
path = inp.get("file_path") or inp.get("path")
if not path:
    sys.exit(0)

target = Path(path)
if not target.is_absolute():
    target = root / target

log = root / ".claude" / "evidence" / "session-changes.jsonl"
log.parent.mkdir(parents=True, exist_ok=True)
record = {
    "ts": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
    "tool": data.get("tool_name"),
    "path": str(target.resolve(strict=False)),
}
with log.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps(record, sort_keys=True) + "\n")
sys.exit(0)
