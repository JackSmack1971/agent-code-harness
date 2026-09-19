---
name: reconciling-state
description: Diagnose resume, worktree, repository, configuration, policy, candidate, destination, or lock drift without silently continuing mutation.
disable-model-invocation: true
user-invocable: true
context: fork
agent: repository-researcher
---
# Reconcile State

Compare persisted and live identities. Classify outcome as MATCH, SAFE_HARNESS_OWNED_DRIFT, EXTERNAL_DRIFT, MISSING_WORKTREE, or CORRUPT_STATE. Recommend the contracted runtime state transition. Never auto-rebase or assume stale lock ownership.
