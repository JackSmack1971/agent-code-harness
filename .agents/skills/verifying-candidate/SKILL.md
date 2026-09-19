---
name: verifying-candidate
description: Independently run the verification ladder against the exact current candidate and classify mandatory criteria.
---

## Execution context

Run this workflow in a fresh Codex subagent using the `verification-engineer` custom-agent role. The primary agent remains the supervisor and must synthesize the returned evidence. The child must not spawn another child. If the named role cannot be started, report the missing execution dependency rather than silently substituting a different authority or review context.

# Verify Candidate

Bind candidate identity first. Run focused, affected broad, structural/invariant, and negative-path checks. Classify each mandatory criterion using PASS/FAIL/ERROR/INCONCLUSIVE/NOT_APPLICABLE. Never reuse stale evidence after candidate mutation.
