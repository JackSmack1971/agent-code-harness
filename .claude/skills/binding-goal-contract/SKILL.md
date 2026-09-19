---
name: binding-goal-contract
description: Convert a software objective into a precise evidence-bound GoalContract or identify blocking user-resolvable ambiguity. Use at the start of a new harness implementation objective.
disable-model-invocation: false
user-invocable: true
context: fork
agent: repository-researcher
---
# Bind Goal Contract

1. Read current repository/phase evidence.
2. Separate repository-resolvable uncertainty from genuinely user-resolvable uncertainty.
3. Resolve repository-resolvable facts from code/contracts/tests.
4. Draft objective, constraints, acceptance criteria, exclusions, uncertainties, and revision identity.
5. Do not smuggle implementation choices into user intent.
6. Return `GOAL_READY` or `BLOCKED_USER_INPUT`.
