---
name: closing-phase
description: Run the final read-only phase closure gate after implementation, verification, invariant audit, and intent review are complete.
disable-model-invocation: true
user-invocable: true
context: fork
agent: release-gatekeeper
---
# Close Phase

Apply `.claude/references/release-gatekeeper-contract.md`. Phase closure is allowed only on PASS. FAIL or INCONCLUSIVE reopens implementation with exact unmet criteria. Never repair while gating.
