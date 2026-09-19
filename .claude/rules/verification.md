---
paths:
  - "src/**/verification/**"
  - "src/**/review/**"
  - "tests/**"
---
# Verification Rules

Verification ladder:
A baseline/reproduction
B focused verification
C broad regression
D structural/invariant verification
E intent conformance

Statuses:
PASS, FAIL, ERROR, INCONCLUSIVE, NOT_APPLICABLE.

- Bind every VerificationResult to exact candidate identity.
- Candidate mutation invalidates affected evidence.
- Required unavailable checks do not become PASS.
- Waivers require explicit policy-authorized evidence.
- Generated tests are supporting evidence, not ground truth.
- Independent reviewer context/route must remain meaningfully independent where required.
