---
paths:
  - "tests/**"
  - "pyproject.toml"
  - ".github/workflows/**"
---
# Testing Rules

- Prefer deterministic, network-free contract tests for foundational behavior.
- Every state/config/event/identity/security contract needs negative tests, not only happy paths.
- Use golden fixtures for canonical bytes, digests, transition behavior, config resolution, event envelopes, and CLI envelopes.
- Add property tests where state transition or canonicalization invariants are combinatorial.
- Recovery tests must include process-kill/interruption and external drift.
- Security tests must include traversal, symlink, taint, redaction, scope-widening, and stale-approval paths as applicable.
- Tests must assert exact semantics rather than merely absence of exceptions.
