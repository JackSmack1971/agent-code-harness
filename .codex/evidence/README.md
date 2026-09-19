# Codex control-plane evidence

This directory stores lightweight project-local execution hints only. It is not the product's authoritative audit ledger.

- `current-phase.txt` — operator-maintained active phase identifier.
- `session-changes.jsonl` — append-only hints emitted by the PostToolUse hook for `apply_patch` operations.
- `closures/` and `gatekeeper/` — reserved for explicit closure tooling; normal apply-patch editing is blocked by the path-policy hook.

Do not treat absence of a record here as proof that no change occurred. Git state and executed evidence are authoritative.

## Runtime-observation boundary

Do not copy raw Chronos registry state, rollout data, Heartbeat internal state, prompts, responses, tool arguments/output, credentials, or absolute paths here. If an experiment needs Chronos evidence, store only a bounded normalized reference/summary with provider provenance, coverage, and its `ExecutionBinding`; canonical product evidence belongs in the product's governed evidence/state model once implemented.
