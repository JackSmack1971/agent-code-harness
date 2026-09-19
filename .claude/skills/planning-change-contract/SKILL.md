---
name: planning-change-contract
description: Produce an evidence-bound ChangeContract and VerificationPlan for a Tier 2 or phase-closing repository change.
disable-model-invocation: false
user-invocable: true
context: fork
agent: repository-researcher
---
# Plan Change Contract

1. Bind the current Goal revision and repository snapshot.
2. Identify affected invariants/contracts and allowed paths.
3. Define the smallest coherent implementation slices.
4. Define focused, broad, structural, and intent verification before implementation.
5. Identify effects/capabilities requiring approval.
6. Identify research gates or blockers.
7. Return `PLAN_READY` only when success can be evaluated deterministically.
