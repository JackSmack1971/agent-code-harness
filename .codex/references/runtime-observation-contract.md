# Runtime Observation Contract — Chronos Integration

## Purpose

This contract defines how the project control plane may consume bounded runtime observations from Chronos without transferring authority from deterministic project policy, verification, or release gates.

Chronos is an optional runtime-observation provider. It may supply evidence about task liveness, token/context behavior, subagent topology, review/approval amplification, test transitions, Git/build state, runtime degradation, and recovery. It does not authorize effects, widen scope, prove intent conformance, close phases, or promote defaults.

## Authority Boundary

The governing relationship is:

`Chronos observes -> harness binds semantics -> evaluation interprets -> policy authorizes -> verification proves -> promotion remains governed.`

Chronos observations MUST NOT:

- grant filesystem, shell, network, Git-history, MCP, secret, or external-write authority;
- replace sandbox, approval, path, effect, or release-gate policy;
- convert a missing check into PASS;
- prove that a task satisfied intent or acceptance criteria merely because runtime health is good;
- automatically rewrite `AGENTS.md`, Skills, agent definitions, routing policy, hooks, or verification policy;
- automatically promote an experimental configuration or `QualifiedDefault`.

## Provider Capability

Chronos is Windows-focused and MUST remain optional unless the product support contract explicitly makes it mandatory. Capability is tiered; installation alone does not prove full supervision.

### Capability tiers

- `CHRONOS_NATIVE` — `chronos.cmd` and native read-only status/Inspector/Heartbeat surfaces are available. A native Governor claim or `recurrenceEligible=true` belongs to this tier and is **not** proof of host-managed supervision.
- `CHRONOS_OBSERVATION` — runtime evidence is actually observed for one or more supported families or lifecycle hooks. Coverage remains family-specific and may still be `partial` or `unsupported`. Trusted/configured hooks without observed dispatch do not satisfy this tier as fully available.
- `CHRONOS_SUPERVISION` — the Codex host exposes the required task inventory/transport and automation surfaces, and host-side postconditions prove exactly one active matching Governor recurrence and zero worker recurrences. Native state alone cannot establish this tier.

A consumer MUST preserve tier state explicitly using values such as `available`, `partial`, `unsupported`, `unavailable`, or `host_verification_required` as appropriate. Do not collapse all tiers into one `chronos_installed` Boolean.

The read-only `scripts/check_chronos.ps1` preflight may be used to inspect native/observation state and record whether host task/automation capability has been independently established. It MUST NOT install Chronos, trust hooks, initialize a Governor, create a recurrence, or mutate host tasks.

Provider or tier absence MUST NOT silently weaken mandatory product verification. A metric that requires Chronos evidence and cannot be validly obtained is `INCONCLUSIVE` unless another explicitly contracted provider supplies equivalent evidence.

## Host-Surface Boundary

Full Chronos supervision depends on host capabilities that may not exist in every Codex CLI surface. In particular, the host must be able to list/verify tasks, create or reuse a dedicated Governor task, manage the Governor recurrence/automation, and verify the recurrence postcondition.

The following are explicitly insufficient to claim `CHRONOS_SUPERVISION`:

- plugin installation alone;
- trusted/configured hooks alone;
- `hookExecutionObservation=not_observed`;
- a native Governor claim alone;
- `recurrenceEligible=true` alone;
- Heartbeat engine availability with all families `unsupported`.

When host task or automation surfaces are unavailable, record supervision as `unavailable`; when the native layer cannot prove those host surfaces, record `host_verification_required`. Continue using lower Chronos tiers when valid rather than treating the entire provider as failed.

## Coverage Semantics

Every Chronos-derived metric MUST retain the source coverage label:

- `observed` — sufficient evidence exists for the stated observation;
- `partial` — evidence exists but is insufficient for a complete conclusion;
- `unsupported` — the runtime/provider does not expose the required evidence.

`partial` and `unsupported` MUST NOT be normalized to zero, healthy, false, or PASS.

For control-plane verification mapping:

- a required metric with `observed` coverage may be evaluated normally;
- a required metric with `partial` or `unsupported` coverage is `INCONCLUSIVE` unless an authorized equivalent source resolves the requirement;
- optional metrics may remain unevaluated, but the missing-data denominator MUST remain visible in experiments and reports.

## Provenance

A persisted Chronos-derived observation used for evaluation MUST retain enough provenance to establish at least:

- provider name (`chronos`);
- Chronos/plugin version when exposed;
- collector/Heartbeat family or Inspector source;
- capture or observation window;
- coverage label;
- source epoch and sequence when supplied by Heartbeats;
- stable event ID when an emitted Heartbeat event is used;
- task/generation identity binding when available;
- the harness execution binding that gives the observation project meaning.

Do not persist raw Chronos registry state, raw rollout transcripts, raw prompts, raw responses, tool arguments, tool output, credentials, or absolute paths into `.codex/evidence/`.

## Semantic Binding

Chronos intentionally does not know the complete project-semantic identity of work. Before a Chronos observation can be used for governed evaluation, the harness MUST bind it to the relevant execution semantics defined in `execution-binding-v1.md`.

At minimum, evaluation should be able to resolve the relevant subset of:

- execution ID;
- phase;
- Goal revision;
- Change revision;
- slice or WorkPackage;
- Skill identity/version;
- custom-agent role/configuration digest;
- candidate/repository identity;
- VerificationPlan or verification evidence;
- experiment identity when the run belongs to a governed experiment.

An observation that cannot be bound to the population being evaluated MUST NOT be counted in that population.

## Observation Classes

Chronos may inform, when its coverage supports them:

- task stalls and repeated-equivalent-action episodes;
- token/usage velocity and tokens since meaningful change;
- compaction, rollout growth, fork depth, context overlap, and child creation;
- automatic-review and approval amplification;
- task/subagent lifecycle and generation changes;
- test state transitions and repair attempts;
- Git/build state transitions;
- machine/runtime degradation;
- intervention attempts and independently verified recovery.

Chronos Heartbeat warnings are heuristic/runtime findings. They are not canonical product failures unless an independent product contract defines that mapping.

## Experiment Use

Phase-12 experiments may consume Chronos metrics only when:

1. baseline and candidate executions use a declared observation protocol;
2. execution bindings identify population membership;
3. coverage and missing-data counts are retained;
4. correctness, safety, scope, and verification guardrails remain primary;
5. negative and inconclusive results are retained;
6. observed reductions are not restated as guaranteed future savings;
7. runtime findings do not auto-promote the candidate.

Typical secondary metrics include repeated-equivalent actions, tokens since meaningful change, compaction count, context overlap, child creation/fork depth, review amplification, stall incidence, and duration. Primary success criteria should normally remain correctness/verification outcomes rather than minimum token usage.

## Integration Boundary

Do not copy or merge Chronos plugin hooks into `.codex/config.toml` or `.codex/hooks/`. Project hooks keep their existing responsibilities. Chronos remains independently installed/trusted and may coexist with project hooks.

The control plane consumes normalized observations through a future provider adapter or experiment harness; it does not own Chronos internal state.
