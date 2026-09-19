# Claude Code Project Control Plane

This `.claude/` tree is project-scoped and designed specifically for implementing the Agentic Coding Harness blueprint.

## Start

1. Commit this package at repository root.
2. Start Claude Code from the repository root.
3. Verify hooks are visible with `/hooks`.
4. Set `.claude/evidence/current-phase.txt` to the active phase, e.g. `P00`.
5. Begin with the phase requirements in `.claude/references/phase-registry.md`.
6. Use lifecycle skills for bounded operations.
7. Use `closing-phase` only after verification, audit, and intent review evidence exists.

## Safety

The hooks are guardrails for the development environment only. They do not implement the product's runtime policy engine.

`settings.json` is intentionally conservative and may require adjustment to the repository's actual test/lint command names after the package skeleton exists.
