# Architecture Boundaries

These rules apply repository-wide.

- Models may recommend actions but cannot own authority, state transitions, approvals, evidence validity, or success semantics.
- Deterministic runtime components own authorization, execution, persistence, verification gating, and acceptance.
- Complexity escalation must follow: deterministic -> localized single-agent -> planned repository change -> bounded specialist delegation.
- Recursive agents are prohibited in v1.
- Later memory, skills, MCP, and adaptive behavior remain subordinate to the same policy/evidence/replay boundaries.
- Do not introduce architectural shortcuts that collapse policy, execution, and verification into one model-mediated operation.
