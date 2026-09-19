# ExecutionBinding v1 — Semantic Runtime Identity

## Purpose

`ExecutionBinding` associates one runtime execution with the control-plane identities required to interpret external runtime observations, including Chronos evidence. It is a semantic binding contract, not an authority grant and not a replacement for the product's authoritative journal or domain state.

## Required Semantics

A binding MUST identify one execution and MUST NOT ambiguously span multiple candidate identities.

Conceptual fields:

```yaml
schema: execution-binding/v1
execution_id: EXE-...

phase_id: P06

goal_revision: GOAL-...@N        # nullable when not yet applicable
change_revision: CHANGE-...@N    # nullable when not yet applicable
slice_id: SLICE-...              # nullable
work_package_id: WP-...          # nullable

procedure:
  skill_id: implementing-slice   # nullable
  skill_digest: sha256:...       # required when a Skill is under evaluation
  agent_role: implementation-engineer  # nullable
  agent_config_digest: sha256:...       # required when an agent config is under evaluation

candidate:
  repository_identity: sha256:...
  base_commit: ...
  worktree_identity: ...
  candidate_identity: sha256:... # required once a candidate identity exists

runtime:
  provider: chronos              # nullable when no runtime provider is used
  provider_task_identity: ...    # protected/opaque identity only
  provider_generation: ...       # nullable
  observation_window: ...

verification_plan_id: VP-...     # nullable
experiment_id: EXP-...           # nullable outside governed experiments
```

The production schema may use the repository's canonical typed/domain representation rather than YAML. Field names above define semantics, not an implementation mandate.

## Identity Rules

- Bindings are append-only or revisioned once referenced by evaluation evidence; do not silently rewrite historical population identity.
- A candidate mutation that changes canonical candidate identity requires a new or revised execution binding for subsequent observations.
- Skill and agent experiments MUST bind the exact content/configuration digest, not only a human-readable version label.
- A reused runtime task ID with a new Chronos generation is a distinct runtime generation and MUST NOT be conflated with the prior one.
- An observation window MUST not be attributed to multiple competing baseline/candidate configurations.
- Opaque provider identities are routing/correlation evidence only; they are not authorization identities.

## Population Rules

An execution can enter an evaluation population only when the experiment protocol can prove the required binding dimensions. Unbound or ambiguously bound observations remain excluded and count toward missing-data reporting where applicable.

For matched or paired comparisons, the experiment protocol must declare which binding dimensions must match across baseline and candidate runs, such as task class, phase, fixture, candidate baseline, verification plan, or environment profile.

## Persistence Boundary

`.codex/evidence/` may store lightweight references or normalized execution-binding hints for local coordination, but it is not the authoritative product ledger. Product implementation should persist canonical bindings in the product's governed state/evidence model once the corresponding phase introduces that authority.
