# Codex Control Plane Conversion — Build Report

## Disposition

**STATIC/SCHEMA VALIDATION: PASS**

**TARGETED HOOK HARNESS: PASS**

**LIVE CODEX CLI LOAD/EXECUTION: NOT RUN** — no `codex` executable was available in the build environment. This is intentionally reported as unverified rather than inferred from static checks.

## Source → target architecture

The conversion preserves the original control-plane intent while changing ownership to Codex-native surfaces:

- behavioral policy: `CLAUDE.md` → root `AGENTS.md`;
- project runtime defaults: Claude settings → `.codex/config.toml`;
- specialist roles: Claude agent Markdown → `.codex/agents/*.toml`;
- repeatable workflows: Claude skills → `.agents/skills/*`;
- implicit/explicit Skill routing: Claude Skill frontmatter → `agents/openai.yaml`;
- lifecycle guardrails: Claude hooks → current Codex lifecycle-hook schema;
- command escalation policy: `.codex/rules/default.rules`;
- path-scoped behavioral guidance: converted references plus mandatory trigger index in `AGENTS.md`;
- source-control isolation: modeled as orchestration precondition, not falsely represented as a custom-agent permission.

## Validation executed

- parsed `.codex/config.toml` with Python 3.13 `tomllib`;
- parsed all 7 custom-agent TOML files;
- compiled all 5 hook scripts plus validator with Python AST/bytecode compilation;
- verified all 8 Skills contain portable `name` + `description` frontmatter and no Claude-only Skill frontmatter fields;
- verified each Skill has `agents/openai.yaml`;
- verified active Codex artifacts contain no `.claude/` or `CLAUDE_PROJECT_DIR` runtime dependency;
- synthetic `SessionStart` event returned Codex `additionalContext` containing Git/phase state;
- synthetic `PreToolUse/Bash` denied `sudo true` and allowed a benign pytest command;
- synthetic `PreToolUse/apply_patch` denied `.env` mutation and allowed ordinary repository file mutation;
- synthetic `PostToolUse/apply_patch` appended a change record;
- synthetic `Stop` event returned `decision: block` for a tracked changed Python placeholder.

## Important non-equivalences preserved

1. Project instructions and Skill instructions do not grant runtime authority.
2. Project `.codex/config.toml` is a trusted-project default, not administrator-enforced policy.
3. Hooks are defense in depth; some specialized tool paths may bypass ordinary tool-hook routing.
4. Execpolicy rules govern command execution outside the sandbox; they are not a replacement for sandbox configuration.
5. Custom-agent `sandbox_mode` configures that child session but does not create a separate Git worktree.
6. Claude path-glob rule frontmatter has no direct Codex behavioral-policy equivalent; the conversion therefore uses explicit trigger guidance plus reference files instead of pretending Codex natively interprets the old format.

## Chronos runtime-observation integration update

**STATIC INTEGRATION VALIDATION: PASS**

This package now defines a narrow optional Chronos integration without moving runtime observation into the authorization path:

- added `.codex/references/runtime-observation-contract.md`;
- added `.codex/references/execution-binding-v1.md`;
- added the Chronos evidence/authority boundary to `AGENTS.md`;
- extended Phase 6, Phase 9, and Phase 12 closure language for coverage-aware runtime observation and governed experimentation;
- documented Chronos as an independently installed optional plugin rather than embedding it in project hooks/config;
- extended `scripts/validate_control_plane.py` to require the new contracts, key coverage/binding semantics, phase-registry markers, and absence of Chronos implementation leakage into `.codex/config.toml` or `.codex/hooks/`.

Validation for this update:

- `python scripts/validate_control_plane.py` — PASS;
- Python bytecode compilation for the validator and all project hook scripts — PASS;
- Chronos live plugin execution — NOT RUN in this build environment; the integration contract therefore does not claim live provider evidence.

## Chronos capability-tier patch

This build adds a fail-closed, non-mutating capability model for Chronos after live Codex CLI setup demonstrated that native Governor readiness can exist without a host task/automation surface.

Implemented:

- `CHRONOS_NATIVE`, `CHRONOS_OBSERVATION`, and `CHRONOS_SUPERVISION` are distinct capability tiers.
- `recurrenceEligible=true` is explicitly documented as native readiness only, never proof of a live Governor recurrence.
- Trusted/configured hooks are distinct from observed hook execution.
- Missing Codex host task/automation surfaces make supervision unavailable or `host_verification_required` without invalidating lower-tier observations.
- `scripts/check_chronos.ps1` performs read-only native/status/Heartbeat checks and does not install Chronos, trust hooks, initialize a Governor, create a recurrence, or mutate tasks.
- Phase 12 requires capability-tier preservation in governed evaluation.
- The package validator requires the capability contract and preflight markers and continues to prohibit Chronos from being embedded in project hook/config implementations.

Validation performed in the packaging environment:

- `python scripts/validate_control_plane.py` — PASS.
- Python hook syntax validation — included in the validator and PASS.
- ZIP integrity and package-manifest verification — performed during final packaging.

Environment limitation: Windows PowerShell/Codex CLI are not available in the packaging container, so `scripts/check_chronos.ps1` was not live-executed against an installed Chronos runtime here. It is intentionally limited to documented read-only Chronos command surfaces.
