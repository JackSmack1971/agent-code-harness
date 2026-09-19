---
paths:
  - "contracts/**"
  - "src/**/domain/**"
  - "src/**/contracts/**"
  - "tests/**/*contract*"
---
# Domain Contract Rules

Durable domain records include GoalContract, ChangeContract, VerificationPlan, VerificationResult, EvidenceManifest, RepositorySnapshot, CandidateSnapshot, AcceptanceRequest, ApprovalRequest, IntentReviewResult, run/checkpoint/artifact/event records, and model/tool/subagent records.

- Treat goal/change revisions as durable identities, not mutable prose.
- Material objective changes require revision/new-run semantics.
- Invalidate stale approvals, checks, and evidence when their bound identity changes.
- Pydantic models reject unknown fields by default.
- Missing implementation-significant semantics block closure rather than becoming "implementation-defined".
