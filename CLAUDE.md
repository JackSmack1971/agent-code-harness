# Agentic Coding Harness — Implementation Constitution

## Mission

Implement the Agentic Coding Harness defined by the repository's Unified Implementation Blueprint — Implementation Closure Edition.

The governing architectural invariant is:

**MODELS PROPOSE. DETERMINISTIC INFRASTRUCTURE AUTHORIZES, EXECUTES, RECORDS, AND PROVES.**

Claude Code is an implementation environment for this repository. It is not the authority mechanism of the product being built.

## Authority Order

Resolve implementation questions in this order:

1. Closure-amended normative requirements in the Unified Implementation Blueprint.
2. Canonical machine-readable contracts and registries under `contracts/`.
3. Accepted repository ADRs.
4. Existing implementation and tests that do not conflict with higher authority.
5. This Claude implementation constitution.

Never invent an implementation-critical semantic choice when a higher-authority contract is missing or ambiguous. Mark the task blocked and identify the missing contract.

## Foundational Invariants

- Use one canonical serialization implementation for all digest-bearing durable objects.
- Use one authoritative machine-readable source for every canonical registry or vocabulary.
- Runtime code, not a model, owns state transitions.
- Policy and approval authority is deterministic, monotonic, resource-scoped, and fail-closed.
- Mutating harness work executes in isolated Git worktrees.
- Repository, candidate, configuration, policy, approval, evidence, and artifact identities are digest-bound.
- Verification evidence proves only the exact candidate state to which it is bound.
- Any candidate mutation invalidates affected verification evidence.
- SQLite domain state is authoritative operational/resume state.
- The append-only event journal is authoritative audit history.
- JSONL is a deterministic projection/export, not a competing operational source of truth.
- Provider credentials remain outside ordinary sandbox/model-visible context.
- Required checks that cannot validly run are never converted to PASS.
- `ACCEPTED` requires destination integration plus required post-integration verification.
- Live runtime behavior never self-promotes experimental defaults.
- Recursive subagents are prohibited in v1; controlled delegation depth is one.

## Engineering Loop

For every implementation slice:

1. Read the current phase and closure criteria in `.claude/references/phase-registry.md`.
2. Identify the exact normative requirements and affected invariants.
3. Inspect the existing contracts, implementation, and tests before editing.
4. Prefer the smallest coherent slice that can be independently verified.
5. Add or update executable tests/fixtures for new semantics.
6. Run focused verification.
7. Run all broader affected verification.
8. Inspect the final diff and candidate identity.
9. Run independent intent review for phase-closing work.
10. Apply the release gate before claiming phase closure.

## Scope Discipline

Do not:

- redesign settled architecture without explicit authorization;
- duplicate canonical state/config/event/effect/status registries in hand-maintained code;
- silently weaken sandbox, policy, verification, identity, or approval requirements;
- substitute model judgment for deterministic authorization;
- represent degraded isolation as equivalent to container isolation;
- infer PASS from absence of errors or skipped checks;
- hide TODOs, placeholders, `pass`, empty handlers, or unimplemented branches behind green tests;
- auto-resolve destination drift, unsafe lock ownership, or integration conflicts;
- broaden network/path/effect authority because a backend cannot enforce the requested scope.

## Python and Platform Baseline

- Python: `>=3.13,<3.15`.
- Pydantic models reject unknown fields by default.
- SQLite uses a single-writer design with WAL.
- System Git minimum must be frozen in the product manifest before Phase 0 closes.
- Version-sensitive provider, container, MCP, tokenizer, CI, and platform assumptions require current research artifacts before their dependent phase closes.

## Verification Doctrine

Verification is multi-dimensional:

1. baseline/reproduction;
2. focused behavior;
3. broad regression;
4. structural/invariant conformance;
5. independent intent conformance.

Valid check statuses are:

`PASS`, `FAIL`, `ERROR`, `INCONCLUSIVE`, `NOT_APPLICABLE`.

A required `INCONCLUSIVE` or `ERROR` cannot be presented as success. Waivers require explicit policy-authorized evidence.

## Agent Use

Use the primary session for normal implementation coordination.

Delegate only when the work benefits from context isolation, independent review, or specialized analysis. Use the smallest applicable specialist:

- `repository-researcher`
- `implementation-engineer`
- `contract-auditor`
- `security-auditor`
- `verification-engineer`
- `intent-reviewer`
- `release-gatekeeper`

Do not delegate trivial edits or simple lookups. Do not permit a child agent to delegate again.

## Completion Semantics

"Implemented" means all of the following are true:

- required code exists;
- required contracts/fixtures exist;
- relevant tests exist;
- mandatory verification is current for the exact candidate;
- affected invariants pass;
- no implementation-critical placeholder remains;
- the final diff was inspected;
- blockers and residual uncertainty are explicit.

"Phase closed" additionally requires the release-gatekeeper contract in `.claude/references/release-gatekeeper-contract.md`.

Passing tests alone is never sufficient evidence of phase closure.
