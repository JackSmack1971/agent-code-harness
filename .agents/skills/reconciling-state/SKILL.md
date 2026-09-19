---
name: reconciling-state
description: Diagnose resume, worktree, repository, configuration, policy, candidate, destination, or lock drift without silently continuing mutation.
---

## Execution context

Run this workflow in a fresh Codex subagent using the `repository-researcher` custom-agent role. The primary agent remains the supervisor and must synthesize the returned evidence. The child must not spawn another child. If the named role cannot be started, report the missing execution dependency rather than silently substituting a different authority or review context.

# Reconcile State

Compare persisted and live identities. Classify outcome as MATCH, SAFE_HARNESS_OWNED_DRIFT, EXTERNAL_DRIFT, MISSING_WORKTREE, or CORRUPT_STATE. Recommend the contracted runtime state transition. Never auto-rebase or assume stale lock ownership.
