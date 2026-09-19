---
paths:
  - "src/**/persistence/**"
  - "src/**/events/**"
  - "src/**/artifacts/**"
  - "src/**/recovery/**"
  - "tests/**/*event*"
  - "tests/**/*recovery*"
---
# Persistence, Audit, and Recovery Rules

- SQLite domain state is authoritative operational/resume state.
- Append-only event journal is authoritative audit history.
- JSONL is deterministic committed-event projection/export only.
- Content-addressed object storage holds immutable large artifacts.
- Domain mutation and its event commit in the same SQLite transaction.
- Use a single-writer model with WAL.
- Resume reconciles persisted identities against live repository/worktree/config/policy reality before mutation.
- Unsafe external drift -> RECONCILIATION_REQUIRED.
- Uncertain lock ownership is never reclaimed solely because time elapsed.
