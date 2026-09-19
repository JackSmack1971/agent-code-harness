---
paths:
  - "contracts/**/*state*"
  - "src/**/state/**"
  - "src/**/runtime/**"
  - "tests/**/*state*"
---
# State Machine Rules

Canonical v1 states:
CREATED, REPOSITORY_READY, GOAL_BOUND, RECONNAISSANCE, PLAN_READY, IMPLEMENTING,
VERIFYING_FOCUSED, VERIFYING_BROAD, INTENT_REVIEW, READY_FOR_USER, ACCEPTING,
ACCEPTED, REJECTED, BLOCKED, INTEGRATION_CONFLICT, RECOVERY_REQUIRED,
RECONCILIATION_REQUIRED, FAILED, INTERRUPTED.

- Only runtime code commits transitions.
- Every requested transition is audited and validated against the canonical relation and invariants.
- Rejected transitions do not mutate durable state.
- `ACCEPTED` means integrated destination plus required post-integration verification passed.
- Approval alone is not acceptance.
