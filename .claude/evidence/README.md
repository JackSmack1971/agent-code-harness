# Local Development Evidence

This directory is for Claude-development workflow evidence, not the product's runtime evidence store.

Recommended local/CI artifacts:
- `current-phase.txt`
- `session-changes.jsonl`
- `closures/<phase>.json`
- `gatekeeper/<run>.json`

Choose intentionally which evidence files are committed. Phase-closure records intended as repository governance artifacts may be committed; ephemeral session logs normally should not be.
