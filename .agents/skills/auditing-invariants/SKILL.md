---
name: auditing-invariants
description: Audit canonical contracts, security authority, and cross-subsystem invariants before phase closure.
---

## Execution context

Run this workflow in a fresh Codex subagent using the `contract-auditor` custom-agent role. The primary agent remains the supervisor and must synthesize the returned evidence. The child must not spawn another child. If the named role cannot be started, report the missing execution dependency rather than silently substituting a different authority or review context.

# Audit Invariants

Audit canonical-source uniqueness, serialization/digests, state/config/event contracts, durable identity, and any phase-specific cross-contract invariants. If the phase touches policy/security boundaries, separately invoke `security-auditor`.
