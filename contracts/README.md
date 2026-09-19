# Canonical Contracts

Machine-readable, normative sources for the Agentic Coding Harness. Every
document here is either a JSON Schema (Draft 2020-12) or a YAML data
instance validated against one.

Phase 0A scope (current):

- `product_manifest.schema.json` / `product_manifest.yaml` — `ProductManifest v1`.
- `research_register.schema.json` / `research_register.yaml` — `ResearchRegister v1`.
- `meta/contract_meta.schema.json` — required metadata shape (`$schema`, `$id`,
  `x-contract-name`, `x-contract-version`, `additionalProperties`) every
  normative schema in this tree must satisfy.
- `meta/schema_digest_exclusions.schema.json` / `.yaml` — non-semantic
  keywords excluded when a schema document is canonicalized for schema
  identity.

Everything else named in the Phase-0 Contract Closure Gate
(`CanonicalSerialization v1`, `SemanticTypes v1`, `DomainSchemas v1`,
`StateMachine v1`, `EventRegistry v1`, `CLIProtocol v1`, etc.) is out of
scope for this slice and MUST NOT be assumed to exist yet; see
`.claude/references/phase-registry.md`.

Offline conformance tests live in `../tests/` and run with `uv run pytest`.
