---
paths:
  - "contracts/**"
  - "src/**/identity/**"
  - "src/**/serialization/**"
  - "src/**/digest/**"
  - "tests/**/*identity*"
  - "tests/**/*serialization*"
---
# Canonical Identity Rules

- All digest-bearing typed objects use the single canonical serialization implementation.
- Canonical pipeline: typed object -> JSON-compatible schema representation -> canonical UUID/date/Decimal/set/null handling -> lexicographic object-key ordering -> UTF-8 compact JSON -> SHA-256.
- Digest text is `sha256:<64 lowercase hex>`.
- Never add subsystem-local serialization or digest helpers.
- Canonical registries have exactly one machine-readable source consumed by runtime and tests.
- Golden fixtures must prove canonical bytes and digests.
