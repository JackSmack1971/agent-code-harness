# Codex CLI Project Control Plane — Agentic Coding Harness

This package is the Codex-native conversion of the original Claude Code project control plane. It preserves the harness architecture while mapping each control-plane mechanism to Codex conventions instead of emulating Claude-specific metadata.

## Install

Copy the contents of this package to the repository root, commit them, then start Codex from that trusted repository. Set `.codex/evidence/current-phase.txt` to the active phase before phase work.

The project layer is intentionally conservative: `workspace-write`, `on-request`, shell network disabled, lifecycle hooks enabled, and bounded multi-agent concurrency. Project config is a default, not an administrative security boundary. Managed requirements/user policy can restrict it further.

## Native Codex layout

- `AGENTS.md` — persistent repository behavioral policy / implementation constitution.
- `.codex/config.toml` — trusted-project defaults, hooks, sandbox/approval defaults, agent concurrency.
- `.codex/agents/*.toml` — specialized Codex custom-agent roles.
- `.agents/skills/*/SKILL.md` — reusable Codex skills using portable Agent Skills format.
- `.agents/skills/*/agents/openai.yaml` — Codex invocation policy/UI metadata.
- `.codex/hooks/*.py` — Codex lifecycle guardrails/evidence hooks using current hook schemas.
- `.codex/rules/default.rules` — execpolicy rules for escalation-sensitive shell commands.
- `.codex/references/` — phase and closure contracts, runtime-observation/ExecutionBinding contracts, plus converted path-policy references.
- `.codex/evidence/` — lightweight local evidence hints, never a substitute for Git or the harness journal.

## Operational invariants

1. Instructions influence decisions; Codex policy/runtime authorizes effects.
2. Skills are procedures, not permissions.
3. Custom agents are roles/configuration layers, not independent authorization domains.
4. Native subagents do not imply isolated Git worktrees. Create/enter a task-owned worktree before mutating delegated work.
5. Use read-only exploration in parallel; use one implementation owner for overlapping files; use fresh review/verification contexts after implementation.
6. Git diff and executed checks outrank agent summaries.
7. Hooks are defense-in-depth guardrails and observability, not substitutes for sandbox/approval/managed policy.

## Start sequence

1. Confirm repository trust and `git status --short --branch`.
2. For mutating work, create or enter an isolated task worktree.
3. Set the active phase in `.codex/evidence/current-phase.txt`.
4. Start Codex from the intended repository/subdirectory.
5. Confirm the SessionStart hook reports repository identity/phase.
6. Use the lifecycle skills as needed. Explicit-only skills remain available with `$skill-name`.
7. For phase-closing work: verification → invariant/security audit as applicable → independent intent review → `$closing-phase`.
8. On supported Windows hosts, Chronos may be installed separately as an optional runtime-observation provider; keep its plugin hooks independent from project hooks and apply `.codex/references/runtime-observation-contract.md`.

## Optional Chronos integration

Chronos is not bundled into this control plane. When installed and trusted separately, it may provide bounded runtime observations for liveness, usage/context behavior, subagent topology, review amplification, test/Git/build transitions, and recovery. The control plane keeps authority deterministic: Chronos observations must be semantically bound through `execution-binding-v1.md`, retain coverage/provenance, and cannot authorize effects or auto-promote configuration changes.

Do not merge Chronos hooks into `.codex/config.toml`; plugin hooks and project hooks retain separate responsibilities. Provider absence on non-Windows or unsupported runtimes must remain explicit rather than weakening mandatory verification.

Capability is three-tiered:

- `CHRONOS_NATIVE` — local Chronos command/status surfaces work;
- `CHRONOS_OBSERVATION` — hooks or supported runtime families are actually observed with explicit coverage;
- `CHRONOS_SUPERVISION` — host task plus automation surfaces exist and prove one Governor recurrence with zero worker recurrences.

`recurrenceEligible=true` is a native readiness signal, not proof of `CHRONOS_SUPERVISION`. On Codex CLI surfaces that do not expose task/automation control, record supervision as unavailable/host-verification-required and continue using lower tiers where valid. Run `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check_chronos.ps1` for a non-mutating capability preflight.

## Important portability differences from Claude Code

- Claude `CLAUDE.md` → Codex `AGENTS.md`.
- Claude `.claude/agents/*.md` frontmatter → Codex `.codex/agents/*.toml` custom-agent config.
- Claude `.claude/skills` → Codex `.agents/skills`; Claude-only frontmatter is removed.
- Claude `context: fork` + `agent:` → explicit skill instruction to spawn a named fresh Codex subagent.
- Claude `disable-model-invocation` → `agents/openai.yaml` `allow_implicit_invocation`.
- Claude `isolation: worktree` has no direct custom-agent field; worktree isolation is enforced as an orchestration/source-control precondition.
- Claude path-scoped `.claude/rules/*.md` has no direct Codex glob-rule equivalent for behavioral instructions; converted policy files live under `.codex/references/path-policies/`, with mandatory trigger mapping in root `AGENTS.md`.
- Claude settings permissions do not map 1:1. Codex sandbox and approvals are distinct; this package uses project defaults plus hooks/execpolicy without pretending project config is admin-enforced.
- Claude `settings.local.json` and `scheduled_tasks.lock` are deliberately not ported because they are not portable Codex project-control-plane objects.

## Validation

Run:

```bash
python scripts/validate_control_plane.py
```

If `codex` is installed, additionally test the execpolicy file with current CLI commands before relying on it in production. The package does not claim a live Codex runtime test was performed when no Codex executable is present.
