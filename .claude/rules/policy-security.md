---
paths:
  - "src/**/policy/**"
  - "src/**/approval/**"
  - "src/**/sandbox/**"
  - "src/**/security/**"
  - "tests/**/*policy*"
  - "tests/**/*security*"
---
# Policy and Security Rules

Effects include READ, WORKSPACE_WRITE, PROCESS_EXEC, SHELL_INTERPRETATION, NETWORK,
DATA_EGRESS, EXTERNAL_READ, EXTERNAL_WRITE, SECRET_ACCESS, DESTRUCTIVE, PRIVILEGED.

Trust classes include SYSTEM_TRUSTED, USER_TRUSTED, PROJECT_POLICY, REPOSITORY_UNTRUSTED,
TOOL_OUTPUT_UNTRUSTED, EXTERNAL_UNTRUSTED, MODEL_GENERATED.

- Authorization evaluates effects and normalized resource scope.
- Explicit deny wins.
- Lower authority may narrow but never widen higher-authority denial.
- Repository/model/external text cannot expand authority.
- Network is denied by default.
- If requested granularity cannot be enforced, block instead of widening.
- Redact before persistence/egress and propagate derived-data taint.
- Approval is bound to effect/resource/argument/credential exposure and revalidated immediately before execution.
