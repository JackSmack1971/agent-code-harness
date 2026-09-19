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

Phase 0D scope (current addition — deterministic state authority):

- `state_machine.schema.json` / `state_machine.yaml` — `StateMachine v1`
  (Blueprint 3.4, 9.8) **and** `RecoveryProtocol v1` (10.8) in a single
  contract pair, per the Closure text ("`state_machine.yaml` MUST contain
  `recovery_transitions` in addition to forward transitions"). The data file
  is a literal transcription of Blueprint 9.8.3's forward transition table,
  9.8.4's exceptional transitions, and 10.8.2's canonical recovery relation
  — no transition or recovery rule is invented. The schema additionally
  defines the `TransitionCommand` request shape (9.8.2), the
  `RecoveryPlan`/`RecoveryProof` types (10.8.1), and a `ResumabilityPolicy`
  $def that resolves the one genuinely underspecified point in 9.8.5 step 4
  (which committed transitions count as a "resumability boundary") by
  requiring a checkpoint after every committed transition — documented
  explicitly here because it is non-narrowing (pure added durability, never
  a relaxation of any invariant), the same kind of resolution the Phase 0C
  section above records for its own two judgment calls.
  `src/agentic_harness/_state_machine.py` is the sole runtime authority
  permitted to decide a transition or resume request (INV-STATE-001): it
  validates against this contract rather than a hand-maintained copy, checks
  `expected_run_version` with optimistic concurrency before consulting the
  relation, and hard-gates the two commands that target `READY_FOR_USER` and
  `ACCEPTED` behind `INV-STATE-002`/`INV-ACCEPT-001` evidence (missing
  evidence fails closed, so a caller cannot bypass either gate by omission).
  `_invariants.inv_state_001` was rewired to call
  `_state_machine.is_valid_transition` instead of the provisional
  hand-transcribed table it carried before this contract existed (that table
  has been deleted, per the comment it shipped with).
  `RECOVERABLE_SOURCE_STATES` (`BLOCKED`, `INTERRUPTED`, `RECOVERY_REQUIRED`,
  `RECONCILIATION_REQUIRED`, `INTEGRATION_CONFLICT`) are the only states
  `authorize_resume` accepts; it never resolves a target to `ACCEPTED`
  (10.8.2), and it is idempotent by construction (10.8.3) because it is a
  pure function of its inputs — calling it again with an unchanged
  unsatisfied-condition snapshot returns the identical rejection and the
  same `blocker_reason_code`, with zero I/O either time.
- `tests/state_machine/` — golden/adversarial fixtures for every forward
  transition, every exceptional transition, and every recovery relation
  (including all three `INTEGRATION_CONFLICT` dispositions).

Phase 0E scope (current addition — configuration, policy, resource
normalization, and classification/redaction foundation):

- `configuration_schema.schema.json` / `.yaml` — `ConfigurationSchema v1`
  (Blueprint 9.9, 10.6): the canonical top-level configuration tree (24
  keys), the `run`->`runtime` / `routing`->`routes` read-only migration
  aliases (alias+canonical together is `CONFIG_ALIAS_CONFLICT`), ordinary
  precedence order (`built-in defaults < system < user < repository <
  explicit --config < environment overrides < CLI overrides`, which is
  explicitly *not* security authority), the canonical per-platform config
  file locations, the registered `HARNESS_*` environment-override list
  (unregistered variables are never consulted), the 9.9.3 fail-safe
  defaults extended to a complete `EffectiveConfiguration` instance per
  10.6.3's "every top-level section has an explicit strict schema" closure
  rule, and the v1 secret-source registry (`env` only; secret values are
  always `{"source", "name"}` references, never plaintext, in canonical
  configuration). TOML is the sole operator-authored format, parsed with
  the standard-library `tomllib` (read-only, matching the fact this is a
  human-authored file the runtime never writes back out).
  `src/agentic_harness/_config.py` is the runtime implementation: it
  resolves the canonical platform/repository locations (including the
  registered `HARNESS_CONFIG` explicit path), parses TOML, alias-migrates
  and strictly validates each present source document,
  merges them in ordinary precedence while applying
  `apply_security_monotonicity` to every supplied security-bearing layer
  (10.6.1: security authority is an intersection, so a later layer may
  narrow but MUST NOT widen an earlier security constraint). This covers
  the security-relevant `sandbox`/`network`/`data_egress`/`acceptance`/`policy`
  fields via a bool-stricter-wins, deny-wins, allow-list-intersection, or
  classification-ceiling rule per field, never ordinary last-write-wins.
  applies only the registered environment overrides, then validates the
  merged result against `EffectiveConfiguration` before computing
  `ConfigDigest` through the single canonical serialization implementation.
- `policy_contract.schema.json` / `.yaml` — `PolicyContract v1` (Blueprint
  3.7, 9.12, 10.11): the closed 11-value `Effect` set and 7-value
  `TrustClass` set (both now authoritative here, no longer placeholders),
  the decision algebra's eight dimensions and four results
  (`ALLOW`/`APPROVAL_REQUIRED`/`DENY`/`BLOCKED_CAPABILITY`) with its five
  literal combination rules (explicit deny wins; narrower scope wins;
  unavailable enforcement yields `BLOCKED_CAPABILITY`, never a widening; an
  approval can satisfy only an already-permitted requirement; derived data
  inherits max sensitivity/taint with no v1 automatic declassification),
  9.12.6 approval-binding field list and `ALLOW_ONCE`/`ALLOW_RUN`
  semantics, and the 10.11 redaction-source registry (schema
  `x-sensitive` fields, secret-broker exact match, registered credential
  formats; entropy-only detection is advisory only) plus its five
  redaction points. `src/agentic_harness/_policy.py` implements the
  decision algebra as a pure function (`evaluate`) and the
  `requires_new_approval` re-binding check (INV-APPROVAL-002).
- `resource_normalization.schema.json` / `.yaml` — `ResourceNormalization
  v1` (Blueprint 9.12.2/9.12.3, 10.10): the seven normalized resource kinds
  and their per-kind canonical structures (now authoritative; supersedes
  the generic carriers in `semantic_types.schema.json` and
  `domain_schemas.schema.json`, which remain in place as structural
  pass-throughs rather than being restructured), the `ResourcePattern`
  grammar (`EXACT`/`PREFIX`/`GLOB`, `PREFIX` restricted to hierarchical
  kinds, glob never delegated to a shell), the literal eight-step
  `repo_path` normalization procedure, and the required adversarial-vector
  coverage list. `src/agentic_harness/_resource_normalization.py`
  implements that step sequence (symlink-safe resolution, traversal
  rejection, Windows drive/UNC rejection, creation-target ancestor
  anchoring) plus per-kind normalizers for `process` (explicit
  `path_dirs`-only resolution — no implicit ambient PATH/cwd search, which
  is how PATH-shadowing attacks work; interpreter invocations require an
  explicitly normalized script argument), `network_origin` (IDNA encoding,
  trailing-dot collapsing, default-port materialization, IPv4/IPv6-literal
  vs. hostname distinction), `repository_ref` (rejects a leading `-` to
  prevent Git CLI option injection), and `ResourcePattern` matching
  including a `pattern_is_broader_than` scope-widening check.
- Data classification/taint propagation and redaction: `DataClassification`
  and `Taint` shapes were already materialized in
  `semantic_types.schema.json` (Phase 0C); this phase adds the
  *propagation/redaction logic* those shapes don't carry on their own,
  `src/agentic_harness/_classification.py`
  (`max_classification`/`union_taint`/`derive_provenance` for 10.3.8;
  `redact_text`/`redact_value`/`redact_output`/`redact_registered_credential_formats`
  for 10.11, backed by `policy_contract.yaml#/redaction`). `redact_output`
  is the boundary helper that applies all registered sources together before
  persistence or egress. There is
  deliberately no "declassify" function anywhere in this module
  (`tests/test_classification_redaction.py::test_no_declassify_function_is_exported`
  asserts this): v1 defines no automatic secret declassification.
- `tests/configuration_schema/`, `tests/resource_normalization/`,
  `tests/policy_contract/` — golden/adversarial fixtures, same
  `{"def": ..., "value": ...}` convention as `tests/domain_schemas/`.

`EventRegistry v1`, `SideEffectTransactionProtocol v1`, and `PersistenceSchema
v1` are materialized in this repository as the Phase 0F foundation. Their
runtime implementations are `src/agentic_harness/_events.py`,
`_side_effects.py`, and `_persistence.py`; the machine-readable authorities
are the adjacent registry/schema files and `persistence.sql`. Other later
contracts (`CLIProtocol v1`, `ToolProtocol v1`, `VerificationProtocol v1`,
etc.) remain out of scope until their phases are implemented. Wiring the
policy/resource/redaction foundation into an actual sandboxed tool-execution
path (native fs/process/search tools, the container backend, live approval
persistence) remains Phase 2/3 work.

Offline conformance tests live in `../tests/` and run with `uv run pytest`.
