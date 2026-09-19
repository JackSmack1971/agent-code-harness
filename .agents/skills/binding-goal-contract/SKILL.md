---
name: binding-goal-contract
description: Convert a software objective into a precise evidence-bound GoalContract or identify blocking user-resolvable ambiguity. Use at the start of a new harness implementation objective.
---

## Execution context

Run this workflow in a fresh Codex subagent using the `repository-researcher` custom-agent role. The primary agent remains the supervisor and must synthesize the returned evidence. The child must not spawn another child. If the named role cannot be started, report the missing execution dependency rather than silently substituting a different authority or review context.

# Bind Goal Contract

1. Read current repository/phase evidence.
2. Separate repository-resolvable uncertainty from genuinely user-resolvable uncertainty.
3. Resolve repository-resolvable facts from code/contracts/tests.
4. Draft objective, constraints, acceptance criteria, exclusions, uncertainties, and revision identity.
5. Do not smuggle implementation choices into user intent.
6. Return `GOAL_READY` or `BLOCKED_USER_INPUT`.
