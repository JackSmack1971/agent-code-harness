---
name: closing-phase
description: Run the final read-only phase closure gate after implementation, verification, invariant audit, and intent review are complete.
---

## Execution context

Run this workflow in a fresh Codex subagent using the `release-gatekeeper` custom-agent role. The primary agent remains the supervisor and must synthesize the returned evidence. The child must not spawn another child. If the named role cannot be started, report the missing execution dependency rather than silently substituting a different authority or review context.

# Close Phase

Apply `.codex/references/release-gatekeeper-contract.md`. Phase closure is allowed only on PASS. FAIL or INCONCLUSIVE reopens implementation with exact unmet criteria. Never repair while gating.
