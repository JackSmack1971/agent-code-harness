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

Everything else named in the Phase-0 Contract Closure Gate (`DomainSchemas
v1`, `StateMachine v1`, `EventRegistry v1`, `RecoveryProtocol v1`,
`ResourceNormalization v1`, `SideEffectTransactionProtocol v1`,
`CLIProtocol v1`, etc.) is out of scope for this slice and MUST NOT be
assumed to exist yet; see `.claude/references/phase-registry.md`.

Offline conformance tests live in `../tests/` and run with `uv run pytest`.
