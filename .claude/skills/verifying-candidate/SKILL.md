---
name: verifying-candidate
description: Independently run the verification ladder against the exact current candidate and classify mandatory criteria.
disable-model-invocation: true
user-invocable: true
context: fork
agent: verification-engineer
---
# Verify Candidate

Bind candidate identity first. Run focused, affected broad, structural/invariant, and negative-path checks. Classify each mandatory criterion using PASS/FAIL/ERROR/INCONCLUSIVE/NOT_APPLICABLE. Never reuse stale evidence after candidate mutation.
