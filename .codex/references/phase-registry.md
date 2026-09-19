# Canonical Implementation Phase Registry

Source basis: Unified Implementation Blueprint — Implementation Closure Edition v1.1, §6 Implementation Roadmap plus its Closure amendments.

The project advances sequentially unless the blueprint explicitly permits preparatory work. A later phase must not be represented as closed while an earlier required dependency remains open.

## Phase 0 — Skeleton and Contracts

**Deliver**
- package and CLI skeleton
- strict typed configuration
- canonical serialization/digests
- core domain schemas
- canonical event registry and payload schemas
- complete deterministic state machine
- stable CLI machine protocol
- `harness doctor`

**Close only when**
- state-transition property tests pass
- malformed-contract rejection passes
- config alias/precedence/security-monotonicity tests pass
- event schema/replay tests pass
- canonical naming/digest tests pass
- every normative Phase-0 contract has one authoritative machine-readable representation under `contracts/`
- golden fixtures prove canonical bytes, digests, transitions, config resolution, event envelopes, and CLI envelopes
- cross-contract invariants pass
- no Phase-0 implementation-critical semantic choice remains delegated to an implementing agent
- the Closure's revised Phase-0 exit gate is satisfied

## Phase 1 — Transactional Workspace

**Deliver**
- repository snapshot identity
- dirty-state capture/materialization
- worktree lifecycle
- content-addressed artifact store
- Goal/Change revision behavior
- acceptance/integration foundation
- approval lifecycle required by mutation

**Close only when**
- original checkout is preserved
- untracked files cannot leak
- revisions invalidate stale dependent state
- destination mismatch is detected
- worktree disposal/recovery invariants pass

## Phase 2 — Native Tools, Policy, and Evidence Boundaries

**Deliver**
- filesystem/search/process/patch/Git tools
- common tool envelopes
- effect policy
- path/resource normalization
- trust classification
- deterministic data classification
- derived-data taint
- redaction before persistence/egress
- atomic patch behavior

**Close only when**
- traversal/symlink attacks are blocked
- stale patches fail atomically
- model text cannot override denial
- tainted derived data cannot bypass egress policy
- secret values are absent from ordinary events/logs

## Phase 3 — Sandbox and Environment Planning

**Deliver**
- container backend
- explicitly degraded host fallback
- typed EnvironmentPlan
- provisioning evidence precedence
- network capability enforcement

**Research gate**
- supported devcontainer subset
- Docker/Podman/platform behavior
- ecosystem provisioning details
- scoped-network enforcement backend

**Close only when**
- planted host secrets are inaccessible
- network is denied by default
- non-root/resource limits are proved
- unsupported scope blocks rather than widens authority

## Phase 4 — Provider Gateway

**Deliver**
- provider-neutral model interface
- OpenAI, Anthropic, OpenRouter adapters
- route/capability model
- provider authentication boundaries
- continuation-state preservation
- retry behavior and model identity

**Research gate**
- current request/stream/tool/state semantics
- authentication
- capability metadata
- current context/output limits

**Close only when**
- native tool-use/stream/error/state fixtures pass
- opaque provider-native state round-trips
- malformed tool output is rejected
- no hidden-chain-of-thought parsing exists

## Phase 5 — Repository Intelligence + EBCC

**Deliver**
- Repository Intelligence Graph
- lexical/structural/trajectory retrieval
- optional semantic retrieval
- context budgets
- provenance
- artifact-backed large outputs
- checkpoint/recompile
- retrieval telemetry

**Research gate**
- Tree-sitter support matrix
- token-count facilities/calibration

**Close only when**
- repository map is deterministic
- every injected code span has provenance
- overflow is handled by checkpoint/recompilation
- golden retrieval metrics are recorded

## Phase 6 — Tier 1 Localized Agent

**Loop**
`localize -> reproduce -> patch -> focused verification -> broad verification`

**Close only when**
- internal simple-bug suite passes
- unverified success is impossible
- anti-thrashing works and, where runtime observation is available, is corroborated by observed progress/repetition evidence rather than token volume alone
- cost/token/tool accounting is recorded with explicit source and measurement coverage; `partial`/`unsupported` runtime evidence is not converted to zero or PASS

## Phase 7 — Planning + Full Verification Ladder

**Deliver**
- Tier 2 reconnaissance/planning
- coherent slices
- final VerificationPlan
- feasibility/waiver semantics
- structural verification
- independent intent review

**Close only when**
- unauthorized path writes are rejected
- green tests cannot override failed intent
- candidate mutation invalidates stale checks
- required reviewer independence is demonstrated

## Phase 8 — Durable Persistence, Recovery, and Resume

**Deliver**
- complete SQLite/event transaction model
- writer ownership/locking
- checkpoints
- crash recovery
- deterministic per-state resume matrix
- reconciliation workflow

**Research gate**
- platform lock ownership/staleness semantics

**Close only when**
- process-kill recovery tests pass
- event sequence integrity passes
- unsafe external drift blocks continuation
- uncertain lock ownership is never reclaimed solely by elapsed time

## Phase 9 — Controlled Subagents

**Deliver**
- one-level WorkPackage delegation
- child worktrees
- scope/effect enforcement
- serial parent integration
- verification invalidation/replay after integration

**Close only when**
- one writer exists per worktree
- child cannot widen scope
- integrated candidate is reverified
- tasks lacking escalation trigger remain single-agent
- where Chronos is available with observed coverage, runtime evidence confirms one-level delegation and surfaces recursive/session-growth violations without making Chronos a universal correctness dependency

## Phase 10 — Memory and Skills

**Deliver**
`MemoryContract v1` covering canonical fact/value identity, evidence identity, duplicate semantics, supersession/invalidation, expiry, repository/snapshot applicability, classification/egress, and retrieval policy; plus versioned skill manifests with package/resource digests and requested capabilities.

**Close only when**
- live repository evidence overrides stale memory
- skills cannot bypass policy
- only selected skill content enters context
- memory promotion requires evidence

## Phase 11 — MCP

**Deliver**
Supported MCP integration only after refreshed protocol research.

**Close only when**
- supported transports/protocol negotiation are explicit
- all remote tools pass through ordinary policy
- external content starts untrusted
- schema changes invalidate prior approval
- unsupported/new effects fail closed

## Phase 12 — Evaluation, Replay, and Governed Optimization

**Deliver**
- golden suites
- long-horizon/safety/context suites
- replay
- paired experiments
- typed experiment protocols
- ExecutionBinding identity sufficient to associate runtime observations with exact phase/Goal/Change/slice/Skill/agent/candidate/experiment semantics
- provider-aware runtime observation ingestion, with Chronos supported as an optional source for usage, context growth, compaction, delegation topology, thrashing, review amplification, stalls, test transitions, and Git/build transitions
- explicit Chronos capability-tier recording (`CHRONOS_NATIVE`, `CHRONOS_OBSERVATION`, `CHRONOS_SUPERVISION`) so native readiness, observed telemetry, and host-managed recurrence are never conflated
- QualifiedDefault promotion records

**Close only when**
- baseline/candidate comparison is reproducible
- hidden verifier separation exists
- metric populations/denominators are complete, including excluded/unbound executions and missing runtime-observation coverage
- runtime-observation provenance and `observed`/`partial`/`unsupported` coverage are preserved through evaluation
- `recurrenceEligible=true`, trusted hooks, or native Governor state cannot independently satisfy a supervision-required metric; missing host task/automation surfaces remain explicit and do not invalidate lower-tier observations
- safety/regression guardrails can veto alternatives
- runtime cannot auto-promote experimental settings, rewrite control-plane artifacts, or turn a Heartbeat finding directly into a promoted default

## Phase 13 — CI

**Deliver**
- trusted/untrusted GitHub execution separation
- headless machine protocol
- safe approval failure
- explicitly authorized external-write capability only

**Research gate**
- current GitHub Actions event/token/permission semantics

**Close only when**
- fork fixtures receive no privileged secret
- event-specific trust paths are tested
- approval-dependent operations fail closed
- there is no implicit push or privileged mutation

# V1 Release Gate

V1 releases only after:
- every phase-specific closure gate passes;
- security/correctness suites pass;
- version-sensitive research artifacts are current for enabled capabilities;
- supported install/doctor workflow succeeds;
- defined UX gates pass;
- final implementation-determinacy audit passes.
