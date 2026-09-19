# Canonical Contracts

Machine-readable, normative sources for the Agentic Coding Harness. Every
document here is either a JSON Schema (Draft 2020-12) or a YAML data
instance validated against one.

Phase 0A scope:

- `product_manifest.schema.json` / `product_manifest.yaml` — `ProductManifest v1`.
- `research_register.schema.json` / `research_register.yaml` — `ResearchRegister v1`.
- `meta/contract_meta.schema.json` — required metadata shape (`$schema`, `$id`,
  `x-contract-name`, `x-contract-version`, `additionalProperties`) every
  normative schema in this tree must satisfy.
- `meta/schema_digest_exclusions.schema.json` / `.yaml` — non-semantic
  keywords excluded when a schema document is canonicalized for schema
  identity.

Phase 0B scope (current addition — canonical identity foundation):

- `canonical_serialization.schema.json` / `canonical_serialization.yaml` —
  `CanonicalSerialization v1`: the value model, object/key-ordering rules,
  JSON byte rules, digest format, and the frozen golden/adversarial vectors.
  The reference implementation is `src/agentic_harness/_canonical.py`; the
  harness-owned RFC 9562 UUIDv7 generator is `src/agentic_harness/_identity.py`.
- `semantic_types.schema.json` — `SemanticTypes v1`: the sole `$defs`
  registry for shared scalar, identifier, and nested/discriminated-union
  types (`Digest`, `GitOid`, UUIDv7 identifier types, `AcceptanceCriterion`,
  `EvidenceRequirement`, `Uncertainty`, evidence/`Waiver`/`WorkPackage`
  types, `DataClassification`/`Taint`, `InlineTextOrArtifact`). `Effect` and
  `ResourcePattern` are declared here only as structural carriers pending
  `PolicyContract v1` (9.12.1) and `ResourceNormalization v1` (10.10), which
  are later phases and are not duplicated here. The
  `EvidenceRequirement.threshold <= len(claim_refs)` cross-field invariant
  is enforced by `src/agentic_harness/_semantic_validation.py`, not by the
  schema alone.
- `reason_code_registry.schema.json` / `reason_code_registry.yaml` —
  `ReasonCodeRegistry v1`: the sole registry of machine-stable reason codes,
  namespaced per Blueprint 10.5, append-only within a major contract
  version.
- `tests/semantic_types/` and `tests/reason_codes/` — golden/adversarial
  fixtures for the two registries above, per the Updated Contract-Conformance
  Suite (10.19).

Phase 0C scope (current addition — durable domain contracts and invariants):

- `domain_schemas.schema.json` — `DomainSchemas v1` (Blueprint 9.6, 10.3,
  10.15): the sole authoritative $defs registry for every Phase-0/Phase-1
  authoritative record (`GoalContract`, `ChangeContract`,
  `VerificationPlan`, `RepositorySnapshot`, `CandidateSnapshot`,
  `VerificationResult`, `EvidenceManifest`, `ApprovalRequest`,
  `ApprovalGrant`, `IntentReviewResult`, `RunRecord`, `CheckpointRecord`,
  `ArtifactRecord`, `ToolCallRecord`, `ModelCallRecord`,
  `SubagentExecutionRecord`, `AcceptanceRequest`, `IntegrationRecord`,
  `QualifiedDefault`, listed in `x-registered-schemas`) plus their shared
  nested types. Every registered type sets `additionalProperties: false` and
  requires `schema_name`/`schema_version`; every type except `ApprovalGrant`
  (whose blueprint field list has none) carries a `digest`. The runtime
  validator/digest reference implementation is
  `src/agentic_harness/_domain_schemas.py`, which validates strictly against
  this schema and computes/verifies each record's identity digest through
  the single canonical serialization implementation in `_canonical.py`
  rather than a second, hand-maintained Pydantic type hierarchy.
- `cross_contract_invariant_registry.schema.json` /
  `cross_contract_invariant_registry.yaml` — `CrossContractInvariantRegistry
  v1` (Blueprint 9.7): the sole registry of the minimum `INV-*` invariant
  set (identity, goal, revision, approval, state, acceptance, security,
  resources, worktrees, events, tools, verification, secrets), each with a
  stable ID, owning contracts, failure disposition, and executable test
  mapping. The decidable predicate behind each currently-testable invariant
  has a pure-function reference implementation in
  `src/agentic_harness/_invariants.py`; full runtime enforcement (worktree
  isolation, transactional journaling, sandboxed execution, policy engine)
  belongs to later phases per `.claude/references/phase-registry.md`.
- `tests/domain_schemas/` — golden/adversarial fixtures for `DomainSchemas
  v1`, same convention as `tests/semantic_types/` and `tests/reason_codes/`.

Two Phase 0C resolutions worth recording explicitly rather than leaving
implicit:

1. **JSON Schema, not a second Pydantic type hierarchy, is DomainSchemas
   v1's runtime enforcement point.** Blueprint 9.6.1 says durable Pydantic
   models must forbid unknown fields; nothing in this codebase (Phase 0A-0C)
   defines a Pydantic `BaseModel` anywhere, despite `pydantic` being a
   declared dependency. Hand-writing ~30 Pydantic classes that duplicate
   `domain_schemas.schema.json`'s field lists would itself violate the
   stronger, more specific rule in CLAUDE.md Scope Discipline ("do not
   duplicate canonical state/config/event/effect/status registries in
   hand-maintained code") and Canonical Identity Rules ("exactly one
   machine-readable source"). `_domain_schemas.py` therefore validates
   directly against the JSON Schema (equally strict, equally
   unknown-field-rejecting) and computes/verifies digests through
   `_canonical.py`. A future phase that wants a typed Python boundary should
   generate Pydantic models from this schema rather than hand-author a
   second copy.
2. **A single `domain_schemas.schema.json` file, not a
   `contracts/domain_schemas/` directory**, mirrors the established
   `semantic_types.schema.json` pattern (also a single-file $defs registry).
   Blueprint 9.6.1's literal wording ("registered under
   `contracts/domain_schemas/`") describes the persisted-record concept, not
   a mandated filesystem layout; every other Phase 0 contract in this
   repository is a single file per contract, and this one follows suit.

Everything else named in the Phase-0 Contract Closure Gate (`StateMachine
v1`, `EventRegistry v1`, `RecoveryProtocol v1`, `ResourceNormalization v1`,
`SideEffectTransactionProtocol v1`, `CLIProtocol v1`, `PolicyContract v1`,
`PersistenceSchema v1`, `ToolProtocol v1`, `VerificationProtocol v1`, etc.)
is out of scope for this slice and MUST NOT be assumed to exist yet; see
`.claude/references/phase-registry.md`. `domain_schemas.schema.json` and
`cross_contract_invariant_registry.yaml` reference those not-yet-materialized
contracts only as documented structural carriers (`Effect`, `ResourcePattern`,
`NormalizedResource`, integration `strategy`), the same pattern
`semantic_types.schema.json` already established for `Effect`/`ResourcePattern`.

Offline conformance tests live in `../tests/` and run with `uv run pytest`.
