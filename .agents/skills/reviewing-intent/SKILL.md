---
name: reviewing-intent
description: Perform independent intent conformance against Goal/Change acceptance criteria without trusting the implementer's narrative.
---

## Execution context

Run this workflow in a fresh Codex subagent using the `intent-reviewer` custom-agent role. The primary agent remains the supervisor and must synthesize the returned evidence. The child must not spawn another child. If the named role cannot be started, report the missing execution dependency rather than silently substituting a different authority or review context.

# Review Intent

Reconstruct intent from authoritative contracts and acceptance criteria. Inspect candidate and evidence independently. Return CONFORMANT, NON_CONFORMANT, or INCONCLUSIVE with criterion-to-evidence mapping.
