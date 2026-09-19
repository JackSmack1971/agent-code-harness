---
name: auditing-invariants
description: Audit canonical contracts, security authority, and cross-subsystem invariants before phase closure.
disable-model-invocation: true
user-invocable: true
context: fork
agent: contract-auditor
---
# Audit Invariants

Audit canonical-source uniqueness, serialization/digests, state/config/event contracts, durable identity, and any phase-specific cross-contract invariants. If the phase touches policy/security boundaries, separately invoke `security-auditor`.
