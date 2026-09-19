---
name: implementing-slice
description: Execute one authorized coherent implementation slice with tests in an isolated worktree.
---

## Execution context

Run this workflow in a fresh Codex subagent using the `implementation-engineer` custom-agent role. The primary agent remains the supervisor and must synthesize the returned evidence. The child must not spawn another child. If the named role cannot be started, report the missing execution dependency rather than silently substituting a different authority or review context.

# Implement Slice

Input must identify the phase, slice, allowed paths, governing contracts, and required verification.

Execute the implementation-engineer procedure. Do not expand scope. Stop on missing contract or unenforceable authority. Return implementation evidence, not a success claim for the whole phase.
