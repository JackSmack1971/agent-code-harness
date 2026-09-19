# Release Gatekeeper Contract

## Purpose

This contract governs whether an implementation phase—or final V1 release—may be represented as closed.

It is intentionally stricter than "tests pass." Closure requires current evidence that the exact candidate satisfies the authoritative requirements and preserves the blueprint's authority, identity, security, recovery, and verification invariants.

## Inputs

The gatekeeper must resolve or explicitly mark missing:

- `phase_id`
- repository identity
- candidate identity
- configuration/policy identity when relevant
- applicable phase closure criteria
- applicable Closure amendments/IC decisions
- authoritative contracts/registries
- verification results
- intent-review result
- security/contract audit results when applicable
- research artifacts required by the phase
- integration/post-integration evidence for release/acceptance gates

## Gate Algorithm

### G0 — Identity Binding

PASS only if the candidate under review is unambiguously identified and all evidence used by later gates is bound to that candidate or is candidate-independent by contract.

Automatic FAIL:
- verification from an older candidate is presented as current;
- destination integration changes the tree without required re-verification.

### G1 — Contract Determinacy

PASS only if every implementation-significant semantic required by the phase has an authoritative machine contract or an explicitly authorized source.

Automatic FAIL:
- unresolved "implementation-defined" behavior in required scope;
- duplicate hand-maintained canonical state/config/event/effect/status registries;
- runtime behavior contradicts Closure-amended contract authority.

### G2 — Implementation Completeness

PASS only if required production paths are implemented.

Search changed/required scope for:
- TODO/FIXME tied to required behavior;
- `pass`/empty handlers;
- `NotImplementedError`;
- placeholder branches;
- mock-only production paths;
- prose promises with no executable implementation.

A placeholder is allowed only when the governing phase explicitly defers that capability and the disabled/fail-closed contract is itself implemented and tested.

### G3 — Verification Ladder

Require applicable evidence for:
- baseline/reproduction;
- focused verification;
- broad regression;
- structural/invariant conformance;
- independent intent conformance.

Mandatory checks may be `PASS`, `FAIL`, `ERROR`, `INCONCLUSIVE`, or `NOT_APPLICABLE`.

Closure requires all mandatory applicable checks to be PASS unless an explicit policy-authorized waiver contract permits otherwise.

Never infer PASS from skipped/unavailable execution.

### G4 — Security Authority

For phases touching tools, policy, sandbox, network, secrets, egress, approvals, MCP, CI, or external writes, PASS only if evidence shows:

- explicit deny precedence;
- authority cannot be widened by lower-trust text/config;
- requested resource scope is enforceable;
- unsupported granularity blocks rather than widens;
- secret/redaction/egress invariants hold;
- approval identity is correctly bound and stale approval invalidates;
- degraded fallback is labeled and constrained as degraded.

### G5 — Persistence and Recovery

For durable-state phases, PASS only if:

- state/event transaction atomicity is tested;
- replay/event integrity is tested;
- resume reconciles live and persisted identities;
- unsafe external drift does not auto-continue;
- ambiguous lock ownership fails conservatively;
- destructive or external effects are not duplicated across recovery.

### G6 — Research Freshness

For version-sensitive phase dependencies, PASS only when the required implementation-time research artifact exists, identifies versions/dates/sources, and the implementation is compatible with the researched behavior.

Required by roadmap at minimum:
- Phase 3: devcontainer/container/platform/network enforcement
- Phase 4: provider request/stream/tool/state/auth/capability/limits
- Phase 5: Tree-sitter/token counting
- Phase 8: platform lock semantics
- Phase 11: current MCP protocol
- Phase 13: current GitHub Actions trust/token/permission semantics

### G7 — Claim Integrity

PASS only if user-facing documentation and status claims match executable reality.

Automatic FAIL:
- "supported" capability has no qualifying doctor/fixture/evidence;
- host fallback is called equivalent sandboxing;
- passing tests are used to override failed intent;
- approval is called acceptance;
- unverified candidate is called ready/accepted.

## Phase Verdict

Emit exactly one:

- `PASS`
- `FAIL`
- `INCONCLUSIVE`

`PASS` authorizes recording phase closure.
`FAIL` requires corrective implementation.
`INCONCLUSIVE` requires missing evidence or contract resolution before closure.

## Required Verdict Record

```json
{
  "schema": "phase-closure-verdict/v1",
  "phase_id": "P00",
  "repository_identity": "<required>",
  "candidate_identity": "<required>",
  "verdict": "PASS|FAIL|INCONCLUSIVE",
  "gates": {
    "identity_binding": "PASS|FAIL|INCONCLUSIVE|NOT_APPLICABLE",
    "contract_determinacy": "PASS|FAIL|INCONCLUSIVE|NOT_APPLICABLE",
    "implementation_completeness": "PASS|FAIL|INCONCLUSIVE|NOT_APPLICABLE",
    "verification_ladder": "PASS|FAIL|INCONCLUSIVE|NOT_APPLICABLE",
    "security_authority": "PASS|FAIL|INCONCLUSIVE|NOT_APPLICABLE",
    "persistence_recovery": "PASS|FAIL|INCONCLUSIVE|NOT_APPLICABLE",
    "research_freshness": "PASS|FAIL|INCONCLUSIVE|NOT_APPLICABLE",
    "claim_integrity": "PASS|FAIL|INCONCLUSIVE|NOT_APPLICABLE"
  },
  "failed_criteria": [],
  "evidence": [],
  "reopen_work": []
}
```

The verdict record must never contain invented evidence. If a required artifact cannot be found, use `INCONCLUSIVE`.

## Final V1 Release Additions

In addition to every phase being closed, final release requires:

- security and correctness suites passing;
- current research for every enabled version-sensitive capability;
- supported installation and `harness doctor` workflow succeeding;
- defined UX gates passing;
- final implementation-determinacy audit passing;
- final landed-state/post-integration proof where applicable.
