---
name: planning-change-contract
description: Produce an evidence-bound ChangeContract and VerificationPlan for a Tier 2 or phase-closing repository change.
---

## Execution context

Run this workflow in a fresh Codex subagent using the `repository-researcher` custom-agent role. The primary agent remains the supervisor and must synthesize the returned evidence. The child must not spawn another child. If the named role cannot be started, report the missing execution dependency rather than silently substituting a different authority or review context.

# Plan Change Contract

1. Bind the current Goal revision and repository snapshot.
2. Identify affected invariants/contracts and allowed paths.
3. Define the smallest coherent implementation slices.
4. Define focused, broad, structural, and intent verification before implementation.
5. Identify effects/capabilities requiring approval.
6. Identify research gates or blockers.
7. Return `PLAN_READY` only when success can be evaluated deterministically.
