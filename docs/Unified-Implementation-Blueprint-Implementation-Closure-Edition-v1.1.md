# Agentic Coding Harness — Unified Implementation Blueprint — Implementation Closure Edition v1.1

## 1. Executive Summary

The Agentic Coding Harness is a local-first, provider-neutral engineering control system that converts a software objective into a bounded, policy-authorized, evidence-backed repository change. Its central contract is: **models propose; deterministic infrastructure authorizes, executes, records, and proves**. The system binds user intent to durable Goal and Change contracts, operates only in isolated Git worktrees, compiles provenance-bearing repository context, constrains tools through effect- and resource-based policy, and requires verification tied to the exact candidate Git state before acceptance. The architecture deliberately favors deterministic workflows and a single primary agent, escalating to stronger models or bounded subagents only when recorded evidence justifies the added complexity. Runtime state, approvals, evidence, recovery, and integration are durable and auditable. Later adaptive capabilities—memory, skills, MCP, routing optimization, and learned defaults—remain subordinate to the same security, evidence, replay, and human/authorized-CI governance boundaries.

---

## 2. Core Principles / Design Tenets

* **Evidence before action.** User intent becomes a durable `GoalContract`; implementation requires a `ChangeContract` and `VerificationPlan`; consequential claims must resolve to repository state, tool output, durable artifacts, or explicit user input.

* **Deterministic infrastructure holds authority.** Models may recommend plans, routes, tools, transitions, tiers, and fixes, but runtime state machines, policy engines, approval mechanisms, sandboxes, schemas, and verification gates determine what is permitted and what counts as success.

* **Exact state identity is fundamental.** Configuration, contracts, evidence, model routes, repository snapshots, candidate trees, events, and artifacts use canonical serialization and digest-bound identity. Evidence from one Git state cannot prove another state without re-verification.

* **Security is capability-based and fail-closed.** Permissions are evaluated from effects, resources, provenance, reversibility, data classification, and enforceable sandbox boundaries. Repository or model text cannot expand authority. Explicit denial and narrower security scopes take precedence over permissive configuration.

* **Complexity must earn its cost.** Use deterministic execution first, then a localized single-agent loop, then planned multi-component reasoning, and only then bounded specialist/subagent execution. Recursive agents are prohibited in v1.

* **Verification is multi-dimensional.** Test success alone is insufficient. Focused behavior, regression safety, structural/invariant conformance, and independent intent conformance are distinct evidence classes.

* **Adaptation occurs offline under evidence governance.** Retrieval policies, routing, skills, thresholds, and other experimental defaults may evolve only through reproducible evaluation and explicit promotion authority; the live runtime does not self-promote behavior.

The architectural mission and baseline priorities originate in Blueprint v1.2, which defines correctness, repository integrity, operational safety, context efficiency, and auditability as simultaneous objectives. Implementation Decisions adds deterministic implementation contracts rather than redesigning that architecture. Closure v1.2.1 supersedes earlier wording only where an explicit `IC-*` decision resolves a conflict or omission.

---

## 3. Architecture / Framework

### 3.1 Governing Authority Model

The synthesized specification has three authority layers:

1. **Architectural authority — Blueprint v1.2**

   * Mission, product boundaries, topology, lifecycle, execution tiers, EBCC, security architecture, verification architecture, provider abstraction, persistence strategy, evaluation program, and implementation phase order.
2. **Implementation-contract authority — Implementation Decisions**

   * Canonical serialization, identifiers, configuration, trust classes, path semantics, execution-tier defaults, provisioning, network enforcement, data classification, redaction, retention, packaging, experimentation, and research gates.
3. **Conflict-resolution authority — Implementation Closure v1.2.1**

   * Supersedes only the exact earlier rules covered by `IC-*` amendments or clarifications.
   * All unaffected Blueprint and Implementation Decisions requirements remain in force.

Canonical registries, schemas, vocabularies, transition relations, and similar shared contracts must have **one machine-readable representation** consumed by runtime code and tests rather than duplicated hand-maintained definitions.

### 3.2 End-to-End Control Chain

```text
USER INTENT
    |
    v
GOAL CONTRACT
    |
    v
REPOSITORY SNAPSHOT + RECONNAISSANCE
    |
    v
EBCC / REPOSITORY INTELLIGENCE
    |
    v
CHANGE CONTRACT + VERIFICATION PLAN
    |
    v
POLICY / APPROVAL / CAPABILITY GATE
    |
    v
ISOLATED WORKTREE + SANDBOX EXECUTION
    |
    v
CANDIDATE SNAPSHOT
    |
    v
FOCUSED -> BROAD -> STRUCTURAL VERIFICATION
    |
    v
INDEPENDENT INTENT REVIEW
    |
    v
EVIDENCE MANIFEST
    |
    v
READY_FOR_USER
    |
    v
ACCEPTANCE + DESTINATION RECONCILIATION
    |
    v
POST-INTEGRATION VERIFICATION
    |
    v
ACCEPTED / AUDITABLE LANDED STATE
```

Any failure of authority, evidence, identity, safety, or environmental capability diverts execution into an explicit blocked, recovery, reconciliation, conflict, interrupted, rejected, or failed state rather than bypassing the control chain.

### 3.3 Core Domain and Identity Layer

The durable domain consists of at least:

* `GoalContract`
* `ChangeContract`
* `VerificationPlan`
* `VerificationResult`
* `EvidenceManifest`
* `RepositorySnapshot`
* `CandidateSnapshot`
* `AcceptanceRequest`
* `ApprovalRequest`
* `IntentReviewResult`
* run/checkpoint/artifact/event records
* model/tool/subagent execution records

Canonical digest construction uses one serialization contract across the system:

```text
typed object
-> JSON-compatible schema representation
-> canonical UUID/date/Decimal/set/null handling
-> lexicographic object-key ordering
-> UTF-8 compact JSON
-> SHA-256
-> sha256:<64 lowercase hex>
```

No subsystem may create an alternative digest serialization.

Goal and Change revisions are durable identities rather than mutable prose. A materially changed objective requires the appropriate revision/new-run semantics, and stale approvals, checks, or evidence must be invalidated when their bound identity changes.

### 3.4 Runtime State Machine

The canonical v1 state registry is:

```text
CREATED
REPOSITORY_READY
GOAL_BOUND
RECONNAISSANCE
PLAN_READY
IMPLEMENTING
VERIFYING_FOCUSED
VERIFYING_BROAD
INTENT_REVIEW
READY_FOR_USER
ACCEPTING
ACCEPTED
REJECTED
BLOCKED
INTEGRATION_CONFLICT
RECOVERY_REQUIRED
RECONCILIATION_REQUIRED
FAILED
INTERRUPTED
```

The simplified Blueprint state diagram is retained only as conceptual explanation; the Closure state relation is authoritative for executable transition semantics.

Only the runtime may commit transitions. Each requested transition is audited, validated against the canonical relation and state invariants, and either committed or rejected without changing durable state.

`ACCEPTED` specifically means that the candidate has been integrated into the selected destination **and required post-integration verification has passed**. Approval alone does not constitute acceptance.

### 3.5 Execution Strategy and Complexity Governor

Execution proceeds through four escalating tiers:

1. **Tier 0 — deterministic**

   * Known scripted/generated operation.
   * No model interpretation required after action selection.

2. **Tier 1 — localized repair**

   ```text
   localize -> inspect -> reproduce -> patch -> focused verify -> broad verify
   ```

   * No free-form planner or subagent by default.

3. **Tier 2 — planned repository change**

   ```text
   reconnaissance
   -> evidence-bound plan
   -> coherent slices
   -> verify each slice
   -> final intent review
   ```

4. **Tier 3 — specialist/long-horizon**

   * Permitted only after a recorded escalation trigger such as independent workstreams, domain specialization, context isolation, route failure, or mandatory independent review.
   * Subagent depth is limited to one level.

Execution-tier classification remains an **experimental default**. Runtime—not the model—owns the final tier decision.

### 3.6 Evidence-Bound Context Compiler and Repository Intelligence

The EBCC determines what enters each reasoning turn.

Every injected item carries:

* provenance;
* purpose;
* freshness;
* token estimate;
* relevance information;
* required/optional status.

A deterministic Repository Intelligence Graph is built from repository evidence and keyed to Git tree identity. It may include tree structure, language distribution, manifests, tests, CI, project instructions, symbols, imports/dependencies, test/source relationships, and task-relevant history.

Retrieval combines:

```text
lexical evidence
+ structural evidence
+ current-trajectory evidence
+ optional semantic evidence
-> canonical-span deduplication
-> task-conditioned ranking
-> budget fitting
-> provenance-bound context
```

Semantic/vector retrieval is optional and cannot be the sole repository-retrieval mechanism.

Before numeric context-confidence thresholds are empirically calibrated, escalation is driven by deterministic evidence conditions such as unresolved symbols, contradictory facts, absent implicated components, repeated missing-evidence requests, or exhausted context budgets.

### 3.7 Tool, Policy, and Security Plane

All actions are expressed through typed tools and declared effects including:

```text
READ
WORKSPACE_WRITE
PROCESS_EXEC
SHELL_INTERPRETATION
NETWORK
DATA_EGRESS
EXTERNAL_READ
EXTERNAL_WRITE
SECRET_ACCESS
DESTRUCTIVE
PRIVILEGED
```

Authorization evaluates effects **and** normalized resource scope.

Trust originates from provenance:

```text
SYSTEM_TRUSTED
USER_TRUSTED
PROJECT_POLICY
REPOSITORY_UNTRUSTED
TOOL_OUTPUT_UNTRUSTED
EXTERNAL_UNTRUSTED
MODEL_GENERATED
```

Repository instructions can guide behavior but cannot override policy, sandbox limits, approval requirements, secret handling, or data-egress controls.

Security authority is monotonic: lower-authority configuration may narrow an allowed capability but cannot widen a higher-authority deny. Explicit deny wins.

### 3.8 Sandbox and Environment Boundary

Preferred topology:

```text
Host orchestrator
├── provider adapters / credential holders
├── policy + state + persistence
└── sandbox
    ├── isolated worktree
    ├── required repository toolchain
    ├── non-root execution
    ├── no provider credentials
    ├── no network by default
    └── resource/time/process limits
```

Container execution is preferred/default when supported. Host execution is an explicitly degraded isolation mode and cannot be represented as equivalent sandboxing.

Environment planning follows deterministic evidence precedence:

```text
explicit harness config
> supported devcontainer declaration
> recognized trusted repository setup policy
> CI evidence
> manifests/lockfiles
> conservative fallback
```

Arbitrary README prose is never directly executed merely because it describes setup.

Declared network granularity cannot exceed enforcement capability. A backend capable only of network on/off cannot silently convert a host-scoped request into unrestricted network access.

### 3.9 Workspace and Git Transaction Layer

Mutating work never occurs directly in the user's active checkout.

The harness:

1. snapshots repository identity and relevant dirty state;
2. creates an isolated worktree;
3. reconstructs the selected source snapshot;
4. verifies materialized identity;
5. applies authorized changes there;
6. produces a candidate snapshot;
7. preserves the original user-visible checkout state.

Dirty working-tree data is treated explicitly rather than silently discarded.

Default acceptance is `SQUASH`. Other supported strategies include `CHERRY_PICK`, topology-permitting `FAST_FORWARD`, and non-mutating `PATCH_ONLY`.

Destination drift, dirty destination state, and integration conflicts are never silently resolved.

### 3.10 Persistence, Audit, and Recovery

The persistence architecture is deliberately not pure event sourcing:

```text
SQLite domain state
    = authoritative operational/resume state

append-only event journal
    = authoritative audit history

JSONL
    = deterministic projection/export of committed events

content-addressed object store
    = immutable large artifacts
```

A domain mutation is not committed unless its corresponding event is committed in the same SQLite transaction.

The audit stream uses one versioned event registry with strict payload schemas covering run lifecycle, state transitions, goals/changes/plans, repository/worktree integration, model calls, tool calls, patches, verification, approvals, context, subagents, artifacts, recovery, and reconciliation.

Crash recovery and resume are state-specific. Resume always reconciles persisted identities against repository/worktree/config/policy reality before further mutation.

### 3.11 Provider and Routing Layer

The model layer is provider-neutral and initially supports:

* OpenAI;
* Anthropic;
* OpenRouter;
* optional generic OpenAI-compatible adapters.

Routes are:

```text
Route A -> routes.primary
Route B -> routes.low_cost_candidates[]
Route C -> routes.stronger_candidates[]
Route D -> routes.reviewer
```

A configured model is not automatically qualified. Capability support, continuation semantics, context/output limits, token accounting, and provider-specific state are determined by adapter capability contracts and current implementation-time research.

Provider-native continuation state remains opaque and lossless across adapter round trips.

If a required route lacks an eligible model, execution blocks rather than silently substituting a route with different semantics.

### 3.12 Verification and Independent Review

Verification is a ladder:

```text
Gate A — baseline / reproduction
Gate B — focused verification
Gate C — broad regression
Gate D — structural / invariant verification
Gate E — intent conformance
```

Verification results bind to the exact candidate snapshot.

A mandatory check can be:

```text
PASS
FAIL
ERROR
INCONCLUSIVE
NOT_APPLICABLE
```

A required check that cannot validly run does not become PASS. Waivers require explicit policy-authorized evidence and cannot silently convert absence of evidence into evidence of correctness.

The independent reviewer receives an appropriately independent context and route. Mandatory acceptance criteria with insufficient evidence produce an inconclusive or failed outcome according to the applicable verification contract, not success.

Generated tests are useful evidence but are not treated as ground truth.

### 3.13 Configuration and External Machine Contract

The public configuration vocabulary is canonically:

```text
runtime
workspace
sandbox
policy
providers
routes
context
retrieval
verification
repository_commands
network
data_egress
secrets
parsers
memory
skills
events
telemetry
retention
approvals
acceptance
mcp
doctor
```

Legacy `run` and `routing` are schema-v1 read-only migration aliases for `runtime` and `routes`; canonical and alias forms appearing together are invalid.

Unknown configuration keys fail validation except within explicitly defined extension points.

The headless CLI exposes stable symbolic results plus transport-level exit classes:

```text
0   success
2   invalid usage/config
3   approval unavailable
4   policy denied
5   verification failed
6   unverifiable/inconclusive gate
7   persistence/repository corruption
8   integration conflict
9   interrupted/cancelled
10  unsupported capability/environment
11  provider/external integration failure
12  internal harness failure
```

### 3.14 Memory, Skills, MCP, and Adaptive Optimization

These features are deliberately later-phase extensions of—not exceptions to—the core control plane.

**Memory**

* Must remain subordinate to live repository evidence.
* Requires canonical keys, evidence identity, version/snapshot applicability, supersession/invalidation, expiry, classification, and egress rules before Phase 10 completion.

**Skills**

* Require versioned package identity and immutable resource digests.
* Installation never implies effect permission.
* Skill code executes through normal policy and sandbox controls.

**MCP**

* External descriptions/resources/tool metadata default to untrusted.
* Server declarations cannot self-authorize effects.
* Tool schemas are digest-bound to approval/call identity.
* Schema changes invalidate old approval.
* MCP credentials remain brokered outside model-visible context.

**Adaptive defaults**

* Live execution never self-promotes experimental behavior.
* Promotion requires a completed experiment, immutable evidence, statistical rules, guardrails, and authorized human or trusted-CI approval.

---

## 4. Key Processes / Workflows

### 4.1 Normal Interactive Run

1. **Initialize repository context**

   * Load and validate canonical configuration.
   * Run applicable capability/doctor checks.
   * Capture repository snapshot.

2. **Bind objective**

   * Collect enough repository evidence to interpret the request.
   * Propose `GoalContract`.
   * Validate schema and uncertainties.
   * Resolve deterministic/repository-resolvable uncertainty.
   * Ask the user only for genuinely blocking user-resolvable ambiguity.
   * Persist the Goal revision.

3. **Reconnaissance**

   * Construct/reuse RIG for current Git identity.
   * Retrieve provenance-bearing evidence.
   * Determine execution tier.

4. **Plan**

   * For Tier 1, proceed through localized repair.
   * For Tier 2+, produce evidence-bound plan and smallest coherent slices.
   * Persist `ChangeContract` and `VerificationPlan`.

5. **Authorize**

   * Check path/effect/resource scope.
   * Resolve approvals where needed.
   * Confirm requested capabilities can actually be enforced.

6. **Implement**

   * Create/use isolated worktree.
   * Execute typed tools through policy.
   * Apply atomic, stale-preimage-protected patches.
   * Persist artifacts and tool events.

7. **Verify**

   * Run focused checks.
   * Run broad regression checks.
   * Run structural/invariant checks where applicable.
   * Invalidate stale evidence after candidate changes.

8. **Intent review**

   * Use independent reviewer route/context where required.
   * Evaluate every mandatory acceptance criterion.

9. **Prepare result**

   * Build candidate snapshot and clean evidence manifest.
   * Transition to `READY_FOR_USER`.

10. **Accept or reject**

    * User or authorized CI chooses disposition.
    * Reconcile destination state before integration.

11. **Integrate**

    * Enter `ACCEPTING`.
    * Apply requested acceptance strategy.
    * Preserve candidate on conflict.

12. **Prove landed state**

    * Bind destination tree.
    * Run required post-integration verification.
    * Commit final audit evidence.
    * Enter `ACCEPTED` only after landed-state proof succeeds.

### 4.2 Approval Workflow

1. Runtime detects an effect/resource requiring approval.
2. Create `ApprovalRequest` bound to:

   * effects;
   * normalized resources;
   * argument digest;
   * credential exposure;
   * reversibility;
   * run/tool identity.
3. Obtain `ALLOW_ONCE`, scoped `ALLOW_RUN`, denial, expiry, or revocation.
4. Revalidate request immediately before execution.
5. Any material argument/effect/resource/credential change requires a new approval.
6. Retry behavior must respect grant consumption semantics rather than treating a previous approval as an unlimited wildcard.

**Owner:** runtime policy/approval subsystem. The model may explain why an action is useful but cannot grant its own authority.

### 4.3 Context Compilation Workflow

1. Determine current task/state purpose.
2. Query deterministic repository structure.
3. Run enabled lexical, structural, trajectory, and optional semantic retrieval.
4. Deduplicate canonical spans.
5. Rank according to task and current evidence.
6. Classify sensitivity/provenance.
7. Fit within context budget.
8. Convert oversized outputs into digest-addressed artifacts.
9. Record the compilation and utilization telemetry.
10. Recompile on checkpoint, evidence change, or deterministic missing-context trigger.

**Owner:** EBCC/runtime; model relevance judgments may inform ranking but cannot replace provenance or hard admission rules.

### 4.4 Repository Command Discovery

Repository commands are discovered from deterministic evidence under an explicit precedence model. Conflicting candidate commands cannot become executable authority simply because the model prefers one.

Before a discovered command is executed it must have:

* trustworthy source evidence;
* deterministic command representation;
* effect classification;
* policy authorization;
* appropriate environment plan.

Unresolved command conflicts block or require explicit resolution.

### 4.5 Failure, Recovery, and Resume

When continuation safety cannot be proven:

```text
normal state
-> BLOCKED / INTERRUPTED / RECOVERY_REQUIRED / RECONCILIATION_REQUIRED
```

Resume must evaluate persisted and live state including:

* repository identity;
* worktree identity;
* candidate identity;
* configuration digest;
* policy digest;
* destination state;
* journals/checkpoints;
* ownership/locking state.

Representative outcomes:

```text
MATCH
    -> resume recorded state

SAFE HARNESS-OWNED DRIFT
    -> reconcile, prove consistency, resume

EXTERNAL DRIFT
    -> RECONCILIATION_REQUIRED

MISSING WORKTREE
    -> recover from durable artifacts or RECOVERY_REQUIRED

CORRUPT STATE
    -> FAILED
```

Automatic rebasing of an already verified candidate onto an externally changed destination is prohibited.

### 4.6 Subagent Workflow

1. Primary orchestrator records the reason delegation is justified.
2. Create bounded `WorkPackage`.
3. Reserve cost/token budget before dispatch.
4. Give child an independent worktree and constrained scope.
5. Child returns patch/evidence/artifacts rather than mutating parent state directly.
6. Parent integrates child output serially.
7. Invalidate verification evidence whose bound base no longer matches.
8. Re-run required verification against the integrated candidate.
9. Resolve conflicts as new parent implementation work.

**Owner:** primary orchestrator. Child depth is one.

### 4.7 Experimental Default Promotion

1. Define an `ExperimentProtocol` before evaluation.
2. Bind baseline, candidate, metrics, guardrails, repetitions/seeds, grader version, statistical method, and required effect/non-inferiority threshold.
3. Execute reproducibly.
4. Produce immutable result artifact.
5. Evaluate primary metric and all safety/regression guardrails.
6. Reject promotion on missing required methodology, unresolved multiple-testing requirements, or guardrail violation.
7. Require explicitly authorized human or trusted-CI promotion decision.
8. Create append-only `QualifiedDefault` record with evidence digests, scope, effective version, and rollback target.
9. Rollback through another governed decision rather than history mutation.

---

## 5. Critical Success Factors & Constraints

### 5.1 Required Conditions

The system succeeds only if:

* all durable identity and hash-bearing objects share the canonical serialization contract;
* configuration, event, state, and other registries have a single canonical machine-readable source;
* repository and candidate states can be reconstructed and compared deterministically;
* writes remain constrained to authorized paths/effects;
* original user checkout state is preserved during normal runs;
* sandbox capabilities are honestly represented and never widened beyond enforceability;
* provider secrets remain outside ordinary sandbox/model/tool-log exposure;
* context items are traceable to evidence;
* stale verification is invalidated after candidate or destination changes;
* success cannot be emitted without required current-state evidence;
* independent review remains meaningfully independent where required;
* recovery is deterministic enough to distinguish safe continuation from required reconciliation;
* every blocked run explains the actionable blocker;
* external/version-sensitive implementation claims are refreshed before the phase that depends on them closes.

### 5.2 Hard Constraints

* Python support begins at `>=3.13,<3.15`; expansion requires CI qualification.
* System Git must satisfy the declared supported minimum.
* Pydantic models reject unknown fields by default.
* SQLite uses a single-writer durable-state design with WAL.
* JSONL is audit output, not a competing operational source of truth.
* Worktree mutation is mandatory for mutating runs.
* Default process execution does not depend on `shell=True`.
* Prompt instructions, repository text, and model output are not security boundaries.
* Recursive subagents are forbidden in v1.
* Semantic/vector retrieval is optional.
* Container isolation cannot be silently replaced by host mode when isolation is required.
* Scoped network requests block when the selected backend cannot enforce the declared scope.
* Binary patch support is outside v1 unless separately specified.
* Headless execution never waits for interactive approval.
* CI cannot expose privileged secrets to untrusted pull-request execution.
* Runtime self-modification and automatic promotion of experimental defaults are prohibited.
* Unsupported or stale safety-critical external behavior fails closed.

### 5.3 V1 Product Boundaries

The following are explicitly non-blocking for v1:

* IDE GUI;
* browser dashboard;
* autonomous PR publishing;
* custom model training;
* permanent multi-agent organizations;
* general-purpose cloud orchestration.

They may be layered later only without weakening the established contracts.

---

## 6. Implementation Roadmap

### 6.1 Near-Term — Establish Deterministic Authority and Safe Execution

#### Phase 0 — Skeleton and Contracts

Deliver:

* package and CLI skeleton;
* strict typed configuration;
* canonical serialization/digests;
* core domain schemas;
* canonical event registry and payload schemas;
* complete deterministic state machine;
* stable CLI machine protocol;
* `harness doctor`.

Dependencies: none.

Exit requirements include:

* state-transition property tests;
* malformed-contract rejection;
* config alias/precedence/security-monotonicity tests;
* event schema/replay tests;
* canonical naming/digest tests;
* every Phase-0 normative contract has one authoritative machine-readable representation under `contracts/`;
* golden conformance fixtures prove canonical bytes, digests, transition behavior, configuration resolution, event envelopes, and CLI envelopes;
* cross-contract invariant tests pass;
* no implementation-critical semantic choice covered by the Phase-0 contracts remains delegated to an implementing agent.

**Critical dependency:** Phase 0 must consume Closure v1.2.1's canonical configuration vocabulary, state registry, event registry, configuration schema, security-authority rules, and frozen package/CLI naming rather than implementing earlier conflicting variants.

#### Phase 1 — Transactional Workspace

Deliver:

* repository snapshot identity;
* dirty-state capture/materialization;
* worktree lifecycle;
* content-addressed artifact store;
* Goal/Change revision behavior;
* acceptance/integration foundation;
* approval lifecycle required by mutating operations.

Depends on: Phase 0 identity/state contracts.

Exit requirements:

* original user checkout preserved;
* untracked files cannot leak;
* revisions invalidate stale dependent state;
* acceptance destination mismatch is detected;
* worktree disposal/recovery invariants pass.

#### Phase 2 — Native Tools, Policy, and Evidence Boundaries

Deliver:

* filesystem/search/process/patch/Git tools;
* common tool envelopes;
* effect policy;
* path/resource normalization;
* trust classification;
* deterministic data classification;
* derived-data taint;
* redaction before persistence/egress;
* atomic patch behavior.

Depends on: Phase 1 workspace boundary.

Exit requirements:

* traversal/symlink attacks blocked;
* stale patches fail atomically;
* model text cannot override denial;
* tainted derived data cannot bypass egress policy;
* secret values absent from ordinary events/logs.

#### Phase 3 — Sandbox and Environment Planning

Deliver:

* container backend;
* declared degraded host fallback;
* typed `EnvironmentPlan`;
* provisioning evidence precedence;
* network capability enforcement.

Depends on: tool/effect model.

Required implementation-time research:

* devcontainer supported subset;
* Docker/Podman/platform behavior;
* ecosystem provisioning details;
* scoped-network enforcement backend.

Exit requirements:

* planted host secrets inaccessible;
* network denied by default;
* non-root/resource limits proved;
* unsupported scope blocks rather than widens authority.

#### Phase 4 — Provider Gateway

Deliver:

* provider-neutral model interface;
* OpenAI, Anthropic, OpenRouter adapters;
* route/capability model;
* provider authentication boundaries;
* continuation-state preservation;
* retry behavior and model identity.

Depends on: configuration, persistence, policy, secret brokerage.

Required implementation-time research:

* current provider request/stream/tool/state semantics;
* authentication;
* capability metadata;
* current context/output limits.

Exit requirements:

* fixture tests for native tool use, streaming, errors, and state;
* opaque provider-native state round-trips;
* malformed tool output rejected;
* no hidden-chain-of-thought parsing.

---

### 6.2 Mid-Term — Add Repository Intelligence, Agentic Execution, and Resumability

#### Phase 5 — Repository Intelligence + EBCC

Deliver:

* RIG;
* lexical/structural/trajectory retrieval;
* optional semantic retrieval;
* context budget controls;
* provenance;
* artifact-backed large outputs;
* checkpoint/recompile behavior;
* retrieval telemetry.

Depends on: provider gateway + repository identity.

Research gate:

* Tree-sitter support matrix;
* token-counting facilities/calibration.

Exit requirements:

* deterministic repository map;
* provenance on every injected code span;
* overflow handled by checkpoint/recompilation;
* golden retrieval metrics recorded.

#### Phase 6 — Tier 1 Localized Agent

Deliver the minimal agentic loop:

```text
localize
-> reproduce
-> patch
-> focused verification
-> broad verification
```

Depends on: tools, provider gateway, EBCC.

Exit requirements:

* internal simple-bug suite;
* no unverified success;
* anti-thrashing;
* cost/token/tool accounting.

#### Phase 7 — Planning + Full Verification Ladder

Deliver:

* Tier 2 reconnaissance/planning;
* coherent implementation slices;
* final VerificationPlan;
* feasibility/waiver semantics;
* structural verification;
* independent intent review.

Depends on: functioning Tier 1 loop.

Exit requirements:

* unauthorized path writes rejected;
* green tests cannot override failed intent;
* candidate mutation invalidates stale checks;
* required reviewer independence demonstrated.

#### Phase 8 — Durable Persistence, Recovery, and Resume

Deliver:

* complete SQLite/event transaction model;
* writer ownership/locking;
* checkpoints;
* crash recovery;
* deterministic per-state resume matrix;
* reconciliation workflow.

Depends on: all earlier durable contracts.

Research gate:

* platform lock ownership/staleness semantics.

Exit requirements:

* process-kill recovery tests;
* event-sequence integrity;
* unsafe external drift blocks automatic continuation;
* uncertain lock ownership never reclaimed purely by elapsed time.

#### Phase 9 — Controlled Subagents

Deliver:

* one-level `WorkPackage` delegation;
* child worktrees;
* scope/effect enforcement;
* serial parent integration;
* verification invalidation/replay after integration.

Depends on: robust persistence/resume and verification.

Exit requirements:

* one writer per worktree;
* child cannot widen scope;
* integrated candidate reverified;
* tasks lacking an escalation trigger remain single-agent.

---

### 6.3 Long-Term — Add Reusable Intelligence, Interoperability, Evaluation, and CI

#### Phase 10 — Memory and Skills

Before completion, add `MemoryContract v1` defining:

* canonical fact/value identity;
* evidence identity;
* duplicate semantics;
* supersession/invalidation;
* expiry;
* repository/snapshot applicability;
* classification and egress;
* retrieval policy.

Also define versioned skill manifests with package/resource digests and requested capabilities.

Depends on: stable evidence and policy infrastructure.

Exit requirements:

* live repository evidence overrides stale memory;
* skills cannot bypass policy;
* only selected skill content enters context;
* memory promotion requires evidence.

#### Phase 11 — MCP

Deliver official supported MCP integration only after current protocol research is refreshed.

Depends on: mature tool/effect/security plane.

Exit requirements:

* supported transports/protocol negotiation;
* all remote tools pass through ordinary policy;
* external content starts untrusted;
* tool-schema changes invalidate prior approval;
* unsupported/new effects fail closed.

#### Phase 12 — Evaluation, Replay, and Governed Optimization

Deliver:

* internal golden suites;
* long-horizon/safety/context suites;
* replay;
* paired experiments;
* typed experiment protocols;
* qualified-default promotion records.

Depends on: stable runtime instrumentation and artifacts.

Exit requirements:

* reproducible baseline/candidate comparison;
* hidden verifier separation;
* full metric populations/denominators;
* regression/safety guardrails can veto cheaper/faster alternatives;
* runtime cannot auto-promote experimental settings.

#### Phase 13 — CI

Deliver:

* trusted/untrusted GitHub execution separation;
* headless machine protocol;
* safe approval failure;
* explicitly authorized external-write capability only.

Depends on: stable headless runtime and policy.

Required current research:

* GitHub Actions event/token/permission semantics.

Exit requirements:

* fork fixtures receive no privileged secret;
* event-specific trust paths tested;
* approval-dependent operations fail closed;
* no implicit push or privileged mutation.

### 6.4 Release Gate

V1 release follows Phase 13 only after:

* all phase-specific closure gates pass;
* security/correctness suites pass;
* version-sensitive research artifacts are current for enabled capabilities;
* supported installation/doctor workflow succeeds;
* defined UX gates pass;
* final implementation-determinacy audit remains satisfied.

---

## 7. Risks, Open Questions & Assumptions

### 7.1 Ranked Risks

| Rank | Risk                                                              | Consequence                                                                         | Required Mitigation                                                                                                              |
| ---- | ----------------------------------------------------------------- | ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| 1    | **Authority drift between documentation and implementation**      | Different components enforce incompatible state/config/event/security rules.        | Canonical machine-readable registries; generated tests/docs; Closure `IC-*` rules supersede only named earlier wording.          |
| 2    | **False success from insufficient verification**                  | Passing tests may mask incomplete behavior or structural requirements.              | Multi-gate verification, criterion-to-evidence mapping, independent intent review, exact candidate binding.                      |
| 3    | **Security scope silently widened by implementation limitations** | Scoped network/path/effect request becomes broader real authority.                  | Privilege monotonicity, enforceability checks, fail-closed `BLOCKED_CAPABILITY`, explicit deny precedence.                       |
| 4    | **Evidence becomes stale after repository/candidate drift**       | Harness presents proof for a state no longer under review.                          | Snapshot/digest binding; invalidation after mutation/integration; reconciliation and mandatory re-verification.                  |
| 5    | **External API/protocol drift**                                   | Provider, MCP, container, CI, tokenizer, or SDK behavior diverges from assumptions. | Version-sensitive research register with phase gates and conservative fallback/disable behavior.                                 |
| 6    | **Crash recovery creates ambiguous ownership/state**              | Duplicate effects, corrupted state, or unsafe continuation.                         | Same-transaction state/event commits, journals, deterministic resume matrix, conservative lock reclamation.                      |
| 7    | **Context retrieval fails silently**                              | Model acts on incomplete or misleading evidence.                                    | Hybrid retrieval, provenance, deterministic missing-context triggers, retrieval telemetry, replay/golden tests.                  |
| 8    | **Subagent complexity exceeds benefit**                           | Longer trajectories, conflicts, cost growth, stale child evidence.                  | Escalation-only delegation, one-level depth, independent worktrees, atomic budget reservation, serial integration.               |
| 9    | **Memory/skills become an alternate authority path**              | Stale or malicious learned artifacts override live policy/evidence.                 | Phase-10 contracts, immutable package identity, evidence-backed memory, ordinary policy enforcement.                             |
| 10   | **Evaluation overfits or promotes weak evidence**                 | Experimental defaults regress production behavior.                                  | Predeclared protocols, guardrails, explicit population/statistics, no runtime auto-promotion, scoped `QualifiedDefault` records. |

### 7.2 Open Questions / Version-Sensitive Decisions

These are **not unresolved architectural contradictions**. They are intentionally deferred implementation facts whose answers must be established at the relevant phase:

* exact supported devcontainer subset;
* ecosystem-specific provisioning profiles;
* Docker/Podman/platform-specific isolation and scoped-egress behavior;
* current OpenAI, Anthropic, and OpenRouter provider API/SDK semantics;
* current provider token-counting and pricing mechanisms;
* qualified Tree-sitter grammars/platform behavior;
* OS-specific lock ownership and stale-lock proofs;
* current MCP protocol/SDK behavior;
* current OpenTelemetry Python exporter/API behavior;
* current GitHub Actions trust/token semantics;
* package-index name availability at publication time.

Where a safety- or continuity-relevant answer is unknown or stale, the affected capability must remain disabled or blocked rather than guessed.

### 7.3 Deferred Contract Work

The following must be resolved before their named phases close:

* **Phase 10:** complete `MemoryContract v1`.
* **Phase 10:** third-party skill package/trust manifest.
* **Phase 11:** MCP effect/schema-change and local-security enforcement.
* **Phase 12:** promotion authority for any adaptive default is governed by the Closure's `QualifiedDefault` process.

### 7.4 Assumptions Preserved from the Sources

* v1 remains primarily a local CLI/TUI system with headless CI support.
* Container execution is preferred where available, but supported host operation remains possible as an explicitly weaker isolation mode.
* A single primary agent is the default topology.
* Python, SQLite, system Git, Pydantic, AnyIO, `httpx`, Typer, Rich, pytest/Hypothesis, and the specified observability/tooling choices remain fixed unless the architecture is formally revised.
* Experimental defaults are adjustable only through evaluation; they are not equivalent to permanent architectural requirements.

### 7.5 Conflict Resolution Status

All implementation-blocking contradictions identified across the three source documents have an explicit governing rule in Closure v1.2.1, including configuration naming, state authority, event taxonomy/payloads, configuration schema, security precedence, public package/CLI naming, revision semantics, approvals, resume behavior, acceptance, CLI protocol, derived-data taint, verification feasibility, repository-command conflicts, and reviewer semantics. The Closure records these as explicit conflict/gap resolutions rather than a redesign of the architecture.

**Remaining unresolved conflicts:** none identified by the source package's final determinacy model.

**Remaining unresolved implementation facts:** the version-sensitive and phase-deferred items listed above.

---

## 8. Appendix

### 8.1 Source Mapping

For this synthesis:

* **Source A — `AGENTIC_CODING_HARNESS_BLUEPRINT_v1.2`**
* **Source B — `IMPLEMENTATION_DECISIONS`**
* **Source C — `IMPLEMENTATION_CLOSURE_v1.2.1`**

| Synthesized Area                               | Primary Source        | Material Contributions from Other Sources                                                                   |
| ---------------------------------------------- | --------------------- | ----------------------------------------------------------------------------------------------------------- |
| Mission, product contract, architecture thesis | A                     | B/C make the contracts implementation-deterministic                                                         |
| Goal → Change → Evidence lifecycle             | A                     | B defines synthesis/scope semantics; C defines revision invalidation                                        |
| Execution tiers / complexity governor          | A                     | B fixes initial tier classifier as an experimental default                                                  |
| EBCC and RIG                                   | A                     | B governs uncalibrated confidence; C preserves algorithmic tuning as experimental                           |
| Tool/effect architecture                       | A                     | B defines trust and exact resource matching; C adds privilege monotonicity                                  |
| Sandbox/environment model                      | A                     | B defines deterministic provisioning and scoped-network rules; C binds implementation research gates        |
| Git/worktree transaction model                 | A                     | B clarifies checkout preservation; C completes acceptance and resume protocol                               |
| State machine                                  | A conceptually        | B consolidates it; **C is final executable transition authority**                                           |
| Configuration                                  | A initial structure   | B defines typed tree; **C resolves canonical names/schema/security authority**                              |
| Event model                                    | A initial audit model | B defines taxonomy; **C defines canonical registry and event payload contracts**                            |
| Persistence/recovery                           | A                     | C completes per-state deterministic resume requirements                                                     |
| Verification ladder                            | A                     | C closes feasibility/waiver/inconclusive and reviewer semantics                                             |
| Provider routing                               | A                     | B fixes route configuration and capability behavior; C fixes canonical `routes` vocabulary                  |
| Approvals                                      | A                     | B supplies scope model; C supplies grant consumption/retry/revocation semantics                             |
| Data classification/redaction                  | A                     | B establishes deterministic baseline; C adds derived-data taint semantics                                   |
| Memory                                         | A                     | B provides preliminary defaults; C requires a Phase-10 `MemoryContract v1`                                  |
| Skills                                         | A                     | C requires versioned immutable package/trust manifest before third-party loading                            |
| MCP                                            | A                     | B/C preserve current-protocol research gate and add local effect/schema security                            |
| Evaluation/replay                              | A                     | B defines experiment protocol; C defines explicit production-promotion authority                            |
| Phase roadmap                                  | A                     | B adds phase closure conditions; C inserts unresolved-contract/research gates into the corresponding phases |
| External compatibility research                | A/B                   | C consolidates the version-sensitive research protocol and fail-closed behavior                             |

Source A explicitly defines itself as the normative implementation specification and fixes the core language, UX, and isolated-worktree execution model. Source B states that it closes implementation-significant ambiguity without replacing the architecture. Source C narrows its amendment authority to conflicts and omissions it explicitly resolves.

### 8.2 Material Conflict Resolutions

| Conflict                                                     | Synthesized Resolution                                                                                     |
| ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| `[run]` vs `[runtime]`                                       | `runtime` is canonical; `run` is migration-only alias.                                                     |
| `[routing]` vs `[routes]`                                    | `routes` is canonical; `routing` is migration-only alias.                                                  |
| Simple vs expanded state machine                             | Closure's complete state registry/relation is authoritative.                                               |
| Different event-name sets                                    | Closure's canonical event registry governs.                                                                |
| Event names without complete payload contracts               | Closure payload registry is required.                                                                      |
| Config precedence vs security authority                      | Value precedence cannot widen security authority; security scope is intersected/fail-closed.               |
| Goal/Change mutation vs durable revisions                    | Material revisions create explicit new revision identities and invalidate dependent evidence as specified. |
| Approval granted vs reusable authorization                   | Consumption, expiry, retry, revocation, resource/effect identity govern reuse.                             |
| User acceptance vs successful integration                    | Only landed + post-integration-verified state is `ACCEPTED`.                                               |
| CLI prose vs automation contract                             | Stable symbolic results and exit classes are mandatory.                                                    |
| Derived summaries vs original sensitivity                    | Derived data inherits governing taint/sensitivity; summarization does not declassify it.                   |
| Unrunnable verification vs implied success                   | Required unverifiable checks are inconclusive/blocked unless a valid explicit waiver exists.               |
| Model-selected repository command vs deterministic authority | Command discovery/conflict resolution follows deterministic evidence and policy.                           |
| Reviewer availability/failure ambiguity                      | Reviewer route, independence, and terminal outcomes follow explicit Closure semantics.                     |

### 8.3 Content Deliberately Not Promoted into Core Architecture

The following source material remains useful but is intentionally kept out of the permanent architectural contract:

* exact RRF weights, retrieval pool sizes, ranking heuristics, and similar RIG/EBCC quality parameters — **experimental defaults**;
* precise recovery-journal file layout, SQLite indexes, helper-class decomposition, and other internal structures — **implementation choices** when external invariants remain unchanged;
* current provider/API/container/MCP/Git/OTel/GitHub behavior — **version-sensitive research**, not timeless architecture;
* current memory-ranking mechanics — deferred until Phase 10 evidence and contract closure;
* package-index publication availability — release-time external fact;
* exact statistical technique for an experiment where the predeclared protocol legitimately selects among supported approaches — governed by the experiment rather than frozen globally.

### 8.4 Rejected Patterns

The unified design expressly excludes:

* default raw `shell=True`;
* regex blocklists as the main security mechanism;
* visible/private chain-of-thought as an execution dependency;
* fixed-provider model IDs as architecture;
* a universal tokenizer assumption;
* head/tail truncation as a general context strategy;
* `git reset --hard` as a complete rollback mechanism;
* treating worktrees as eliminating all concurrency conflicts;
* unsafe shared-SQLite assumptions;
* permanent planner/coder hierarchies;
* mandatory vector databases;
* CI paths that execute untrusted code with privileged secrets;
* treating passing tests as sufficient proof of user intent.

### 8.5 Final System Invariant

```text
USER INTENT
    -> DURABLE GOAL
        -> PROVENANCE-BOUND RECONNAISSANCE
            -> AUTHORIZED CHANGE CONTRACT
                -> POLICY-GOVERNED EFFECTS
                    -> ISOLATED MUTATION
                        -> EXACT-STATE VERIFICATION
                            -> INDEPENDENT INTENT REVIEW
                                -> CONTROLLED INTEGRATION
                                    -> POST-INTEGRATION PROOF
                                        -> AUDITABLE ACCEPTED STATE
```

**Models may propose every step. Deterministic infrastructure owns authority, execution boundaries, durable identity, evidence, recovery, and the definition of success.**


---

## 9. Implementation Contract Appendix v1

### 9.1 Purpose, Authority, and Conformance

This appendix closes the remaining gap between architectural intent and executable implementation. Sections 1–8 remain authoritative for architecture, product boundaries, and system invariants. This appendix is **normative for implementation** wherever it defines exact representation, identity, state, policy, persistence, tool, verification, or CLI behavior.

Where Sections 1–8 already define a rule, this appendix makes that rule executable and must not weaken it. Where Sections 1–8 leave an implementation-significant choice unspecified, this appendix makes a new v1 implementation decision. Such choices are deliberately explicit so that a coding agent does not silently become an architect.

The authoritative contract set is:

```text
contracts/
├── product_manifest.yaml
├── canonical_serialization.schema.json
├── semantic_types.schema.json
├── domain_schemas/
├── reason_code_registry.yaml
├── cross_contract_invariants.yaml
├── state_machine.yaml
├── recovery_protocol.yaml
├── configuration.schema.json
├── event_registry.yaml
├── persistence.sql
├── side_effect_transaction_protocol.yaml
├── policy_contract.yaml
├── resource_normalization.yaml
├── repository_identity.schema.json
├── tool_protocol/
├── verification_protocol.schema.json
├── cli_protocol.schema.json
└── research_register.yaml
```

The repository MAY generate documentation, Python types, validators, test fixtures, migration checks, or CLI help from these artifacts. It MUST NOT maintain a second hand-authored definition that can disagree with them.

A v1 implementation is contract-conformant only when:

1. every normative artifact has a versioned machine-readable source;
2. generated/runtime definitions derive from, embed, or are mechanically checked against that source;
3. required golden vectors and conformance tests pass;
4. unknown enum values, states, effects, event types, protocol variants, and schema fields fail closed unless the relevant contract explicitly defines an extension point;
5. a contract change that changes externally observable semantics increments the affected contract version and supplies an explicit migration/compatibility rule;
6. cross-contract invariants in §9.7 pass as executable tests.

### 9.2 Common Contract Template

Every contract artifact MUST expose the following metadata or its schema-equivalent:

```yaml
contract_name: <stable identifier>
contract_version: 1
status: normative
architecture_version: "1.x"
compatibility: exact | backward_compatible | migration_required
```

Every contract specification MUST define, either directly or by reference:

1. scope;
2. normative vocabulary;
3. machine-readable representation;
4. field/type definitions;
5. normalization/canonicalization rules;
6. invariants;
7. error/failure semantics;
8. compatibility/versioning behavior;
9. golden examples or fixtures;
10. required conformance tests;
11. explicitly undefined/deferred behavior.

“Undefined” does not mean “implementation choice” for security-, identity-, persistence-, or evidence-relevant behavior. Such behavior MUST block until a contract revision defines it.

### 9.3 Dependency Layers

The contract dependency graph is:

```text
FOUNDATION
  ProductManifest v1
  CanonicalSerialization v1
  SemanticTypes v1
  DomainSchemas v1
  ReasonCodeRegistry v1
  CrossContractInvariantRegistry v1

CONTROL
  StateMachine v1
  RecoveryProtocol v1
  ConfigurationSchema v1
  PolicyContract v1
  ResourceNormalization v1
  RepositoryIdentity v1

RUNTIME
  ToolProtocol v1
  EventRegistry v1
  PersistenceSchema v1
  SideEffectTransactionProtocol v1

EXTERNAL MACHINE CONTRACT
  VerificationProtocol v1
  CLIProtocol v1

RESEARCH GOVERNANCE
  ResearchRegister v1
```

A lower layer MUST NOT depend on semantic behavior introduced only by a higher layer. In particular, canonical identity and domain-object validation MUST be usable without provider, model, UI, or network availability.

---

## 9.4 Contract 1 — `ProductManifest v1`

### 9.4.1 Canonical Product Identity

The following are new v1 implementation decisions:

```yaml
product_name: Agentic Coding Harness
distribution_name: agentic-coding-harness
python_import_root: agentic_harness
cli_name: harness
contract_version: 1
```

Package-index availability remains a release-time external fact. If `agentic-coding-harness` is unavailable at publication time, publication MUST block pending an explicit ProductManifest revision; the implementation MUST NOT silently publish under another name while retaining the same manifest version.

### 9.4.2 Support Matrix

```yaml
python:
  specifier: ">=3.13,<3.15"
git:
  source: system
  minimum_version: implementation_research_required
platforms:
  required:
    - linux-x86_64
    - windows-x86_64
  conditional:
    - macos-arm64
    - macos-x86_64
```

The exact minimum Git version MUST be fixed before Phase 0 closes because repository identity and worktree behavior depend on it. Until that research decision is written into `product_manifest.yaml`, `harness doctor` MUST report `UNSUPPORTED_CAPABILITY` for production use rather than guessing.

### 9.4.3 Dependency Policy

Core runtime dependencies are limited to dependencies required by the architecture, including Pydantic, AnyIO, `httpx`, Typer, Rich, SQLite via the Python standard library or a specifically approved adapter, and Git via the system executable. Test-only dependencies include pytest and Hypothesis.

Rules:

* Runtime dependencies MUST use bounded compatible ranges, not unconstrained `*` or bare latest-version resolution.
* Lockfiles used for development/CI MUST be committed.
* A dependency that participates in security boundaries, serialization, provider communication, or persistence MUST be pinned in release builds to a tested version set.
* Optional integrations MUST be extras and MUST NOT become import-time requirements for the base CLI.
* Importing `agentic_harness` MUST NOT perform network access, Git mutation, process execution, configuration mutation, database migration, or credential lookup.

### 9.4.4 Compatibility Policy

Public machine contracts include canonical bytes/digests, durable object schemas, event envelopes, state names, CLI JSON envelopes, symbolic result codes, and persistence migration semantics.

Changes are classified as:

```text
PATCH     internal fix; no public machine-contract change
MINOR     backward-compatible additive contract change
MAJOR     breaking contract or migration semantics
```

A field may be added to a durable v1 object only if its absence has a defined deterministic default or a schema-version migration. Renaming/removing fields, changing digest input, changing enum meaning, or changing success semantics requires a major contract revision even if Python APIs remain source-compatible.

---

## 9.5 Contract 2 — `CanonicalSerialization v1`

### 9.5.1 Scope

This contract governs all digest-bearing durable objects, approval arguments, event payload digests, configuration digests, evidence identities, artifact metadata identities, and schema identities.

Raw file bytes and Git object IDs are not re-serialized; they retain their native byte/object identity and are referenced from canonical objects.

### 9.5.2 Canonical Value Model

Allowed canonical values are:

```text
null
boolean
integer
string
array of canonical values
object with string keys and canonical values
```

Floating-point values are forbidden in identity-bearing canonical objects. A domain that requires decimal quantities MUST use `Decimal` and serialize them as canonical decimal strings.

Additional Python/domain types normalize as follows:

| Type | Canonical representation |
|---|---|
| UUID | lowercase hyphenated string |
| Enum | declared stable string value |
| datetime | UTC RFC 3339, `YYYY-MM-DDTHH:MM:SS[.ffffff]Z` |
| date | `YYYY-MM-DD` |
| Decimal | normalized base-10 string; no exponent; no leading `+`; `-0` becomes `0`; trailing fractional zeros removed |
| Path/resource object | its contract-defined normalized string/object form |
| set/frozenset | array sorted by each element's canonical serialized UTF-8 bytes |
| bytes | forbidden directly; store artifact/digest reference |

Strings MUST be valid Unicode and encoded as UTF-8. Canonical serialization does **not** perform Unicode normalization; changing Unicode code points changes identity. This avoids silently altering repository paths, opaque provider state, or user text.

### 9.5.3 Object Rules

* Object keys MUST be strings.
* Keys are ordered lexicographically by Unicode code point.
* Duplicate keys are invalid before serialization.
* Optional fields that are semantically absent MUST be omitted.
* Fields whose schema value is explicitly `null` MUST be emitted as `null`; omitted and null are distinct.
* Unknown fields are invalid for strict durable schemas.
* Arrays preserve semantic order unless the field schema explicitly declares set semantics.

### 9.5.4 JSON Bytes

Canonical JSON uses:

```text
UTF-8
no BOM
no insignificant whitespace
`,` between members/items
`:` between key/value
lowercase JSON literals true/false/null
JSON string escaping as required for valid JSON
non-ASCII characters emitted as UTF-8 rather than `\uXXXX` solely for ASCII transport
```

The digest is:

```text
sha256:<lowercase hexadecimal SHA-256 of canonical UTF-8 bytes>
```

### 9.5.5 Golden Vectors

These vectors are normative:

| Canonical bytes | Digest |
|---|---|
| `{}` | `sha256:44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a` |
| `{"a":1,"b":true}` | `sha256:d918e8d1a9eb1f54b583326cad9950c771474b5c8ac1072bb0f2a0ad148d6de5` |
| `{"name":"café","none":null,"tags":["a","b"]}` | `sha256:ae302866dc4eabd91aac60b6a6e2e5ed315ff7bf2377da9cd00aa1356c211e49` |
| `{"decimal":"1.23","id":"550e8400-e29b-41d4-a716-446655440000","ts":"2026-09-19T03:38:00Z"}` | MUST be generated and frozen by the repository fixture before Phase 0 closes |

The first three digests above are frozen. The fourth intentionally forces the implementation to use the contract's Decimal and UTC normalization pipeline rather than copying a prose example; its expected digest MUST be generated by the independent golden-fixture generator and then committed once cross-checked by a second implementation.

### 9.5.6 Required Tests

Property/conformance tests MUST prove:

* dictionary insertion order does not affect bytes;
* set iteration order does not affect bytes;
* omitted and null differ;
* float input is rejected;
* equivalent supported timezone representations normalize to one UTC representation;
* decimal spelling differences normalize identically where numerically equal;
* byte-for-byte golden vectors match across the primary serializer and an independent fixture implementation.

---

## 9.6 Contract 3 — `DomainSchemas v1`

### 9.6.1 Global Model Rules

All durable Pydantic models MUST use strict validation, forbid unknown fields, and carry:

```text
schema_name: stable string
schema_version: positive integer
```

Identity-bearing objects MUST expose a `digest` computed from the canonical serialization of their identity payload. The digest field itself MUST NOT be included in its own digest input.

Mutable runtime convenience objects are not automatically durable contracts. Only objects registered under `contracts/domain_schemas/` may be persisted as authoritative domain records.

### 9.6.2 Identifier Types

```text
RunId             UUIDv7 string
GoalId            UUIDv7 string
GoalRevisionId    UUIDv7 string
ChangeId          UUIDv7 string
ChangeRevisionId  UUIDv7 string
PlanId            UUIDv7 string
CheckId           UUIDv7 string
ApprovalId        UUIDv7 string
ToolCallId        UUIDv7 string
EventId           UUIDv7 string
ArtifactId        sha256:<hex>
SnapshotDigest    sha256:<hex>
ConfigDigest      sha256:<hex>
PolicyDigest      sha256:<hex>
```

If the chosen Python runtime/library cannot generate UUIDv7 without an additional dependency, the ProductManifest MUST explicitly approve one; the implementation MUST NOT silently substitute UUIDv4.

### 9.6.3 Identity-Bearing Durable Objects

The minimum v1 schemas are:

#### `GoalContract`

```text
goal_id: GoalId
goal_revision_id: GoalRevisionId
parent_revision_id: GoalRevisionId | null
intent: non-empty string
desired_outcome: non-empty string
constraints: ordered list[string]
acceptance_criteria: ordered list[AcceptanceCriterion]
uncertainties: ordered list[Uncertainty]
created_at: datetime
source: USER | AUTHORIZED_CI
digest: Digest
```

A material change to intent, desired outcome, constraints, or acceptance criteria creates a new `goal_revision_id`; it never mutates the prior revision in place.

#### `ChangeContract`

```text
change_id: ChangeId
change_revision_id: ChangeRevisionId
parent_revision_id: ChangeRevisionId | null
goal_revision_id: GoalRevisionId
base_repository_snapshot: SnapshotDigest
summary: non-empty string
allowed_resources: ordered list[ResourcePattern]
required_effects: set[Effect]
acceptance_criteria: ordered list[AcceptanceCriterionRef]
verification_plan_id: PlanId
created_at: datetime
digest: Digest
```

#### `VerificationPlan`

```text
plan_id: PlanId
change_revision_id: ChangeRevisionId
candidate_binding: LATE_BOUND
checks: ordered list[VerificationCheckSpec]
intent_review: IntentReviewSpec
post_integration_checks: ordered list[VerificationCheckSpec]
created_at: datetime
digest: Digest
```

The plan may be created before a candidate exists. Individual results MUST bind to an exact candidate snapshot.

#### `RepositorySnapshot`

```text
repository_root_identity: string
git_common_dir_identity: string
head_commit: git_oid | null
head_ref: string | null
index_digest: Digest
tracked_worktree_digest: Digest
untracked_manifest_digest: Digest
submodule_manifest_digest: Digest
is_dirty: bool
captured_at: datetime
digest: SnapshotDigest
```

#### `CandidateSnapshot`

```text
run_id: RunId
base_repository_snapshot: SnapshotDigest
worktree_identity: string
head_commit: git_oid | null
tree_digest: Digest
index_digest: Digest
untracked_manifest_digest: Digest
captured_at: datetime
digest: SnapshotDigest
```

#### `VerificationResult`

```text
check_id: CheckId
plan_id: PlanId
candidate_snapshot: SnapshotDigest
check_type: BASELINE | FOCUSED | BROAD | STRUCTURAL | INTENT | POST_INTEGRATION
status: PASS | FAIL | ERROR | INCONCLUSIVE | NOT_APPLICABLE
started_at: datetime
finished_at: datetime
tool_call_ids: ordered list[ToolCallId]
artifact_ids: ordered list[ArtifactId]
claim_refs: ordered list[string]
reason_code: string | null
digest: Digest
```

#### `EvidenceManifest`

```text
run_id: RunId
change_revision_id: ChangeRevisionId
candidate_snapshot: SnapshotDigest
criterion_evidence: ordered list[CriterionEvidence]
verification_result_digests: ordered list[Digest]
review_result_digest: Digest | null
created_at: datetime
digest: Digest
```

#### `ApprovalRequest`

```text
approval_id: ApprovalId
run_id: RunId
tool_call_id: ToolCallId
effects: set[Effect]
resources: ordered list[NormalizedResource]
argument_digest: Digest
credential_exposure: NONE | BROKERED | MODEL_VISIBLE | TOOL_VISIBLE
reversibility: REVERSIBLE | CONDITIONALLY_REVERSIBLE | IRREVERSIBLE
requested_scope: ONCE | RUN
created_at: datetime
expires_at: datetime | null
digest: Digest
```

#### `ApprovalGrant`

```text
approval_id: ApprovalId
request_digest: Digest
disposition: ALLOW_ONCE | ALLOW_RUN | DENY
actor_type: USER | TRUSTED_CI
actor_id: string | null
issued_at: datetime
expires_at: datetime | null
revoked_at: datetime | null
consumption_limit: integer | null
consumed_count: integer
```

#### `IntentReviewResult`

```text
run_id: RunId
candidate_snapshot: SnapshotDigest
reviewer_route: string
reviewer_model_identity: string
independence_context_digest: Digest
criterion_results: ordered list[CriterionReview]
overall_status: PASS | FAIL | INCONCLUSIVE
artifact_ids: ordered list[ArtifactId]
created_at: datetime
digest: Digest
```

### 9.6.4 Ordinary Durable Records

At minimum:

```text
RunRecord
CheckpointRecord
ArtifactRecord
ToolCallRecord
ModelCallRecord
SubagentExecutionRecord
AcceptanceRequest
IntegrationRecord
QualifiedDefault
```

Their full JSON Schemas MUST be committed before the first phase that persists them. A phase MUST NOT write an unregistered ad hoc JSON object to authoritative state and later treat it as a durable contract.

---

## 9.7 Contract 4 — `CrossContractInvariantRegistry v1`

The invariant registry is machine-readable and test-addressable. Each invariant has a stable ID, severity, owning contracts, executable test references, and failure disposition.

Minimum registry:

```text
INV-IDENTITY-001
Every VerificationResult.candidate_snapshot equals the exact CandidateSnapshot
against which its evidence was produced.
Failure: invalidate result; block success.

INV-IDENTITY-002
Every EvidenceManifest.change_revision_id and candidate_snapshot must match the
currently governed Change revision and candidate.
Failure: RECONCILIATION_REQUIRED or re-verification.

INV-GOAL-001
A ChangeContract must reference an existing Goal revision belonging to the same run.
Failure: reject persistence.

INV-REVISION-001
A material Goal/Change revision invalidates dependent approvals, plans, checks, reviews,
and evidence whose bound identity is no longer equal.
Failure: remove them from current-valid view; history remains append-only.

INV-APPROVAL-001
A grant authorizes only the ApprovalRequest digest to which it is bound.
Failure: policy denied / approval required.

INV-APPROVAL-002
Changed effects, normalized resources, arguments, credential exposure, reversibility,
or tool schema identity require a new ApprovalRequest.

INV-STATE-001
Only StateMachine v1 may authorize a runtime-state transition.

INV-STATE-002
READY_FOR_USER requires a current EvidenceManifest covering every mandatory acceptance
criterion without unresolved required FAIL/ERROR/INCONCLUSIVE state.

INV-ACCEPT-001
ACCEPTED requires completed integration to the selected destination and required
post-integration verification against the landed destination identity.

INV-SECURITY-001
Effective authority is never broader than the intersection permitted by all applicable
higher-authority security constraints.

INV-SECURITY-002
Repository text, tool output, external content, or model-generated content cannot create
new capabilities or expand policy.

INV-RESOURCE-001
Resource authorization occurs after canonical normalization and before side effects.

INV-WORKTREE-001
A mutating tool call for a governed run targets the run's isolated worktree, never the
user's original checkout.

INV-EVENT-001
A committed authoritative domain mutation has a corresponding committed event in the
same SQLite transaction.

INV-EVENT-002
Event sequence numbers are strictly increasing per run with no duplicate committed
sequence number.

INV-TOOL-001
Tool result success cannot be emitted for a partially applied atomic operation.

INV-VERIFY-001
An unrunnable mandatory check cannot be represented as PASS.

INV-VERIFY-002
A candidate mutation invalidates all verification/review evidence bound to the prior
candidate identity unless the check contract explicitly proves candidate-independence.

INV-SECRET-001
Secret plaintext must not appear in ordinary event payloads, JSONL projections, model
transcripts, or persisted tool outputs.
```

A release MUST fail if any required invariant has no executable test mapping.

---

## 9.8 Contract 5 — `StateMachine v1`

### 9.8.1 States

The canonical states are exactly those in §3.4. No aliases are accepted in persisted state.

### 9.8.2 Transition Command Model

A transition request is:

```text
transition_id: UUIDv7
run_id: RunId
from_state: State
to_state: State
command: stable symbolic command
expected_run_version: integer
precondition_evidence: ordered list[Digest]
requested_at: datetime
```

The runtime MUST compare `expected_run_version` using optimistic concurrency. A stale request is rejected without mutating state.

### 9.8.3 Canonical Forward Transitions

| From | Command | To | Minimum guard |
|---|---|---|---|
| `CREATED` | `bind_repository` | `REPOSITORY_READY` | repository snapshot valid |
| `REPOSITORY_READY` | `bind_goal` | `GOAL_BOUND` | current Goal revision persisted |
| `GOAL_BOUND` | `begin_reconnaissance` | `RECONNAISSANCE` | repository identity still matches |
| `RECONNAISSANCE` | `finalize_plan` | `PLAN_READY` | Change + VerificationPlan persisted |
| `PLAN_READY` | `begin_implementation` | `IMPLEMENTING` | required authorization/environment available |
| `IMPLEMENTING` | `begin_focused_verification` | `VERIFYING_FOCUSED` | candidate snapshot captured |
| `VERIFYING_FOCUSED` | `focused_passed` | `VERIFYING_BROAD` | required focused checks current and passing/not-applicable |
| `VERIFYING_FOCUSED` | `repair` | `IMPLEMENTING` | failure is remediable and policy permits |
| `VERIFYING_BROAD` | `broad_passed` | `INTENT_REVIEW` | required broad/structural gates satisfied |
| `VERIFYING_BROAD` | `repair` | `IMPLEMENTING` | remediable failure |
| `INTENT_REVIEW` | `review_passed` | `READY_FOR_USER` | current EvidenceManifest complete |
| `INTENT_REVIEW` | `repair` | `IMPLEMENTING` | review identifies remediable gap |
| `READY_FOR_USER` | `accept` | `ACCEPTING` | acceptance authorization valid; destination reconciled |
| `READY_FOR_USER` | `reject` | `REJECTED` | authorized disposition |
| `ACCEPTING` | `integration_verified` | `ACCEPTED` | landed identity + post-integration proof valid |
| `ACCEPTING` | `integration_conflict` | `INTEGRATION_CONFLICT` | conflict detected; candidate preserved |
| `ACCEPTING` | `destination_drift` | `RECONCILIATION_REQUIRED` | destination no longer matches precondition |

### 9.8.4 Exceptional Transitions

Any nonterminal active state MAY transition to:

```text
BLOCKED                  when a known external/actionable prerequisite is absent
INTERRUPTED              on operator cancellation or controlled process interruption
RECOVERY_REQUIRED        when durable state exists but safe continuation cannot be proven
RECONCILIATION_REQUIRED  when persisted identity and live external state disagree
FAILED                   on non-recoverable invariant, corruption, or internal failure
```

`REJECTED`, `ACCEPTED`, and `FAILED` are terminal for that run revision.

`BLOCKED`, `INTERRUPTED`, `RECOVERY_REQUIRED`, `RECONCILIATION_REQUIRED`, and `INTEGRATION_CONFLICT` MUST persist a `resume_target_state` or `recovery_plan`. Resume is permitted only after the state-specific reconciliation procedure proves the guard for that target. No generic “set state back” operation exists.

### 9.8.5 Transition Effects

Every committed transition MUST atomically:

1. update the run state and increment `run_version`;
2. append `state.transition.committed` with from/to/command/evidence;
3. apply contract-defined invalidations;
4. persist a checkpoint when the target is a resumability boundary.

A rejected transition appends `state.transition.rejected` only if the event store itself is healthy; it MUST NOT alter the authoritative state.

---

## 9.9 Contract 6 — `ConfigurationSchema v1`

### 9.9.1 Files and Precedence

Canonical configuration file format is TOML for operator-authored configuration. The runtime validates it through `configuration.schema.json` after parsing and alias migration.

Ordinary value precedence, lowest to highest:

```text
built-in defaults
< system config
< user config
< repository config
< explicit --config file
< environment overrides explicitly registered by schema
< CLI value override explicitly registered by schema
```

Security authority is **not** ordinary precedence. Effective security scope is the intersection of all applicable constraints; a lower layer may narrow but never widen a higher-authority deny.

### 9.9.2 Canonical Top-Level Tree

Only these top-level keys are accepted in schema v1:

```text
runtime
workspace
sandbox
policy
providers
routes
context
retrieval
verification
repository_commands
network
data_egress
secrets
parsers
memory
skills
events
telemetry
retention
approvals
acceptance
mcp
doctor
extensions
```

`run` is a read-only migration alias for `runtime`; `routing` is a read-only migration alias for `routes`. Alias and canonical key appearing together is invalid. `extensions` is the only general extension point and MUST namespace each extension by a reverse-DNS or package-qualified identifier.

### 9.9.3 Required Defaults

The schema MUST encode at least these fail-safe defaults:

```yaml
runtime:
  headless: false
  execution_tier: auto
  max_subagent_depth: 1

workspace:
  mutation_mode: isolated_worktree
  preserve_original_checkout: true

sandbox:
  backend: auto
  require_non_root: true
  host_fallback: explicit_only

network:
  default: deny
  scoped_request_on_unenforceable_backend: block

data_egress:
  default: deny

policy:
  unknown_effect: deny
  unknown_resource_type: deny
  repository_text_can_expand_authority: false

verification:
  unrunnable_required_check: inconclusive
  stale_candidate_evidence: invalidate

approvals:
  headless_behavior: fail
  default_scope: once

acceptance:
  strategy: squash
  require_destination_reconciliation: true
  require_post_integration_verification: true

events:
  jsonl_projection: true

memory:
  enabled: false

skills:
  enabled: false

mcp:
  enabled: false
```

Provider, route, command, retention, telemetry, parser, and doctor sections MUST define explicit schemas before use; they MUST NOT accept arbitrary dictionaries except at declared extension payload fields.

### 9.9.4 Secret Configuration

Secret values MUST be references, never plaintext values in canonical configuration. The schema accepts secret-reference objects such as:

```json
{"source":"env","name":"OPENAI_API_KEY"}
```

Supported secret sources are versioned capabilities. Unknown sources fail validation.

### 9.9.5 Configuration Identity

The effective non-secret configuration plus stable secret-reference metadata is canonically serialized and hashed to `ConfigDigest`. Secret plaintext is excluded. A change to effective policy-relevant configuration invalidates authorization/evidence according to the invariant registry.

---

## 9.10 Contract 7 — `EventRegistry v1`

### 9.10.1 Event Envelope

Every event is:

```text
event_id: EventId
run_id: RunId
sequence: integer >= 1
event_type: registered string
event_version: integer >= 1
occurred_at: datetime
actor_type: RUNTIME | USER | CI | MODEL | TOOL | SUBAGENT | SYSTEM
actor_id: string | null
causation_event_id: EventId | null
correlation_id: string | null
payload: registered strict object
payload_digest: Digest
redaction_applied: bool
```

`sequence` is allocated transactionally and is strictly increasing per run. Wall-clock time is not ordering authority.

### 9.10.2 Minimum Registry

The canonical v1 registry MUST include strict payload schemas for at least:

```text
run.created
run.blocked
run.interrupted
run.failed
state.transition.requested
state.transition.committed
state.transition.rejected
repository.snapshot.captured
worktree.created
worktree.disposed
goal.revision.created
change.revision.created
verification.plan.created
approval.requested
approval.granted
approval.denied
approval.revoked
approval.consumed
model.call.started
model.call.completed
model.call.failed
tool.call.requested
tool.call.authorized
tool.call.completed
tool.call.failed
patch.applied
candidate.snapshot.captured
verification.check.started
verification.check.completed
verification.evidence.invalidated
intent_review.started
intent_review.completed
evidence.manifest.created
acceptance.requested
integration.started
integration.conflict
integration.completed
post_integration.completed
artifact.stored
checkpoint.created
recovery.started
recovery.completed
reconciliation.required
reconciliation.completed
subagent.dispatched
subagent.completed
context.compiled
```

New event types require registry modification and conformance tests. Arbitrary free-form event names are prohibited.

### 9.10.3 Redaction and Projection

Payload validation and redaction occur before persistence. Redaction MUST preserve field shape where practical and replace secret values with typed redaction markers; it MUST NOT store plaintext and later “clean” projections.

JSONL is produced from committed SQLite event rows in sequence order. A JSONL line is the canonical JSON representation of the event envelope followed by exactly one LF byte (`0x0A`). JSONL is never replayed as operational authority when SQLite state is available.

---

## 9.11 Contract 8 — `PersistenceSchema v1`

### 9.11.1 SQLite Authority

SQLite is the authoritative operational/resume store. Required database properties:

```text
journal_mode = WAL
foreign_keys = ON
single logical writer
explicit transactions
schema version recorded in database metadata
```

The implementation MUST NOT depend on cross-process concurrent writes to one database as a supported v1 behavior.

### 9.11.2 Minimum Tables

`persistence.sql` MUST define at least:

```text
schema_meta(
  schema_version PK,
  applied_at,
  migration_digest
)

runs(
  run_id PK,
  state,
  run_version,
  goal_revision_id,
  change_revision_id,
  repository_snapshot_digest,
  candidate_snapshot_digest,
  config_digest,
  policy_digest,
  resume_target_state,
  created_at,
  updated_at
)

goal_revisions(
  goal_revision_id PK,
  goal_id,
  parent_revision_id,
  canonical_json,
  digest UNIQUE,
  created_at
)

change_revisions(
  change_revision_id PK,
  change_id,
  goal_revision_id FK,
  parent_revision_id,
  canonical_json,
  digest UNIQUE,
  created_at
)

verification_plans(
  plan_id PK,
  change_revision_id FK,
  canonical_json,
  digest UNIQUE,
  created_at
)

verification_results(
  check_id PK,
  run_id FK,
  candidate_snapshot_digest,
  status,
  canonical_json,
  digest UNIQUE,
  valid INTEGER,
  created_at
)

approvals(
  approval_id PK,
  run_id FK,
  request_digest,
  disposition,
  canonical_json,
  consumed_count,
  revoked_at,
  created_at
)

artifacts(
  artifact_digest PK,
  media_type,
  byte_length,
  storage_relpath,
  classification,
  created_at
)

events(
  event_id PK,
  run_id FK,
  sequence,
  event_type,
  event_version,
  occurred_at,
  canonical_json,
  payload_digest,
  UNIQUE(run_id, sequence)
)

checkpoints(
  checkpoint_id PK,
  run_id FK,
  run_version,
  state,
  canonical_json,
  digest UNIQUE,
  created_at
)

integrations(
  integration_id PK,
  run_id FK,
  strategy,
  destination_before,
  destination_after,
  canonical_json,
  created_at
)
```

Additional normalized/index tables are allowed, but authoritative object bytes/digests MUST remain reconstructible.

### 9.11.3 Transaction Rule

For every authoritative domain mutation:

```text
BEGIN IMMEDIATE
  validate expected identities/version
  write domain mutation
  allocate next event sequence
  write corresponding event
COMMIT
```

If the event write fails, the domain mutation rolls back. If the domain write fails, no success event may commit.

### 9.11.4 Migrations

* Migrations are forward-only in production state.
* Every migration has a stable ID and source digest.
* Startup MUST refuse a database schema newer than the running binary understands.
* Failed migration leaves the previous committed schema authoritative.
* Destructive migration requires an explicit backup/export step and ProductManifest compatibility declaration.
* Test fixtures MUST cover upgrade from every still-supported prior schema version.

### 9.11.5 Content-Addressed Artifact Store

Artifact path is derived from digest and MUST NOT be supplied by model text. Recommended layout:

```text
objects/sha256/ab/cd/<remaining-hex>
```

Writing is temp-file + fsync where supported + atomic rename. Existing digest collision with differing bytes is a corruption condition and transitions the run to `FAILED`.

---

## 9.12 Contract 9 — `PolicyContract v1`

### 9.12.1 Effects

Effects are exactly:

```text
READ
WORKSPACE_WRITE
PROCESS_EXEC
SHELL_INTERPRETATION
NETWORK
DATA_EGRESS
EXTERNAL_READ
EXTERNAL_WRITE
SECRET_ACCESS
DESTRUCTIVE
PRIVILEGED
```

Unknown effects deny.

### 9.12.2 Resource Kinds

V1 normalized resource kinds are:

```text
repo_path
process
network_origin
external_service
secret
repository_ref
artifact
```

Each resource has a canonical structured representation. Policy matching occurs against normalized resources, never raw user/model strings.

### 9.12.3 Path Normalization

For `repo_path`:

1. input must be relative to the governed worktree unless the tool contract explicitly permits another root;
2. reject NUL and invalid platform path encodings;
3. collapse `.` components;
4. reject any `..` that escapes the authorized root;
5. resolve existing symlinks before authorization;
6. for creation targets, resolve the nearest existing ancestor and prove the unresolved suffix cannot escape through a symlink race under the tool's atomicity strategy;
7. compare using platform-appropriate canonical case semantics;
8. authorize the final resolved target, not only the lexical input.

### 9.12.4 Trust

Trust classes are exactly those in §3.7. Trust is provenance metadata, not a scalar permission score. No untrusted class can authorize an effect.

### 9.12.5 Decision Algebra

A policy decision evaluates:

```text
requested effects
× normalized resources
× provenance/trust
× data classification/taint
× reversibility
× sandbox enforceability
× applicable approvals
× higher-authority denies
```

Result:

```text
ALLOW
APPROVAL_REQUIRED
DENY
BLOCKED_CAPABILITY
```

Rules:

* explicit deny wins;
* narrower scope wins over broader scope;
* unavailable enforcement yields `BLOCKED_CAPABILITY`, never an implicit widening;
* an approval can satisfy only an approval requirement already permitted by policy; it cannot override a hard deny;
* derived data inherits the maximum governing sensitivity/taint of its inputs until an explicit declassification mechanism exists; v1 defines no automatic declassification by summarization.

### 9.12.6 Approval Binding

An approval request binds to effect set, normalized resources, argument digest, credential exposure, reversibility, run ID, tool-call identity, and tool-schema digest. Any material difference requires a new approval.

`ALLOW_ONCE` is consumed atomically immediately before the authorized side effect begins. A tool failure after consumption does not restore the grant. `ALLOW_RUN` remains usable until expiry/revocation but only for requests matching its explicit scope predicate.

---

## 9.13 Contract 10 — `RepositoryIdentity v1`

### 9.13.1 Scope

Repository identity must distinguish committed state, staged state, tracked working-tree modifications, untracked content, submodule state, and governed worktree identity.

### 9.13.2 Git Preconditions

Supported repositories are non-bare Git worktrees using the qualified system Git version. SHA-1 and SHA-256 object formats MAY be supported only if doctor capability detection and tests prove both; otherwise ProductManifest must declare the supported object format. The implementation MUST NOT infer OID length globally.

### 9.13.3 Snapshot Construction

A `RepositorySnapshot` captures:

```text
Git common-dir identity
worktree root identity
HEAD symbolic ref if any
HEAD commit OID if any
index canonical digest
tracked worktree manifest digest
untracked manifest digest
submodule manifest digest
relevant sparse-checkout metadata if supported
dirty boolean
```

Ignored files are excluded from candidate semantic identity by default but MUST be considered by safety checks if a tool may overwrite them. If ignored files are intentionally materialized into the sandbox environment, that materialization is separately recorded.

### 9.13.4 Dirty State

Dirty source state is never silently dropped. A run must choose one of:

```text
CLEAN_BASE
CAPTURE_DIRTY_STATE
BLOCK_DIRTY_STATE
```

If captured, tracked/staged/untracked input content is materialized into the isolated worktree using content-addressed artifacts and the resulting materialized identity is verified before mutation.

### 9.13.5 Candidate Identity

Candidate semantic identity is based on the exact files that would constitute the candidate change, not merely `HEAD`. A new candidate snapshot MUST be captured after every successful mutating tool transaction that can affect verification semantics.

### 9.13.6 Acceptance Reconciliation

Before integration, capture destination identity again. If it differs from the destination identity assumed by the acceptance request, enter `RECONCILIATION_REQUIRED` unless the selected strategy's contract explicitly proves the new state equivalent. Automatic rebasing of a verified candidate is prohibited.

---

## 9.14 Contract 11 — `ToolProtocol v1`

### 9.14.1 Common Request Envelope

```text
tool_call_id: ToolCallId
run_id: RunId
tool_name: registered string
tool_version: integer
tool_schema_digest: Digest
arguments: strict tool-specific object
argument_digest: Digest
requested_effects: set[Effect]
requested_resources: ordered list[NormalizedResource]
expected_candidate_snapshot: SnapshotDigest | null
timeout_ms: integer | null
```

Policy is evaluated over the normalized request generated by deterministic tool code. A model MAY suggest effects/resources, but the tool implementation computes authoritative effects/resources from validated arguments.

### 9.14.2 Common Result Envelope

```text
tool_call_id: ToolCallId
status: SUCCESS | FAILURE | TIMEOUT | CANCELLED | DENIED | BLOCKED_CAPABILITY | STALE_PRECONDITION
started_at: datetime
finished_at: datetime
exit_code: integer | null
stdout: InlineTextOrArtifact | null
stderr: InlineTextOrArtifact | null
artifacts: ordered list[ArtifactId]
pre_candidate_snapshot: SnapshotDigest | null
post_candidate_snapshot: SnapshotDigest | null
error: ToolError | null
```

A tool MUST NOT return `SUCCESS` if the operation's atomicity guarantee was not met.

### 9.14.3 Error Schema

```text
code: stable symbolic string
category: VALIDATION | POLICY | ENVIRONMENT | PROCESS | FILESYSTEM | GIT | NETWORK | PROVIDER | INTERNAL
message: human-readable redacted string
retryable: bool
details: strict redacted object
```

Stable symbolic error codes are machine contract; free-form message text is not.

### 9.14.4 Filesystem Tools

Filesystem writes require an expected preimage state where overwriting existing content. Writes use temp-file + atomic replace when the platform supports the required semantics. A changed preimage yields `STALE_PRECONDITION` and no write.

### 9.14.5 Patch Tool

Text patch requests MUST bind each changed file to a preimage digest. The complete multi-file patch is validated before first mutation. If any precondition fails, zero files are changed. If the platform cannot provide all-or-nothing semantics for the requested patch shape, the tool MUST stage the result in a temporary tree and atomically promote the candidate representation or reject the operation.

Binary patch mutation is unsupported in v1 unless a later tool-contract version defines it.

### 9.14.6 Process Tool

Process execution uses argv arrays by default and does not invoke a shell. `SHELL_INTERPRETATION` is a separate effect and requires an explicitly shell-typed tool/request path.

Process contract includes:

```text
argv
cwd
sanitized environment
stdin mode
stdout/stderr capture mode
timeout
process-group termination behavior
resource limits
network capability context
```

Timeout/cancellation MUST attempt process-tree termination within the backend's proven capability and report if complete termination cannot be established.

### 9.14.7 Git Tools

Git operations use deterministic argv and explicitly selected worktree/repository roots. Mutating Git commands require the same policy and snapshot preconditions as filesystem writes. `git reset --hard` is not a rollback primitive for arbitrary run state.

### 9.14.8 Output Artifactization

Inline tool output has a configured byte limit. Larger outputs are stored as artifacts; the result contains digest, byte length, media type, and a bounded preview. Truncation without an artifact reference is forbidden when omitted bytes could affect later evidence or debugging.

---

## 9.15 Contract 12 — `VerificationProtocol v1`

### 9.15.1 Distinguish Checks from Claims

A passing check is evidence, not a conclusion by itself. Acceptance criteria are proven through explicit criterion-to-evidence mappings.

```text
AcceptanceCriterion
  -> one or more required EvidenceClaims
      -> one or more VerificationResults / artifacts / repository facts
```

### 9.15.2 Verification Check Specification

```text
check_id: CheckId
name: stable string
check_type: BASELINE | FOCUSED | BROAD | STRUCTURAL | INTENT | POST_INTEGRATION
required: bool
command_or_mechanism: typed union
expected_effects: set[Effect]
resource_scope: ordered list[ResourcePattern]
timeout_ms: integer
success_predicate: typed predicate
feasibility_policy: FAIL | INCONCLUSIVE | WAIVER_ALLOWED
criterion_refs: ordered list[string]
```

### 9.15.3 Status Semantics

```text
PASS            check executed and success predicate is satisfied
FAIL            check executed and produced valid evidence of non-conformance
ERROR           check could not complete because execution itself failed
INCONCLUSIVE    execution/evidence cannot establish the required proposition
NOT_APPLICABLE  contract proves the check does not apply to this candidate
```

`NOT_APPLICABLE` requires an applicability rule, not model preference.

### 9.15.4 Waivers

A waiver is a durable typed record:

```text
waiver_id
check_id / criterion_ref
candidate_snapshot
reason_code
justification
policy_authority
actor
issued_at
expires_at | null
```

A waiver does not rewrite a result to PASS. It changes whether a non-PASS result blocks a specific gate under explicit policy.

### 9.15.5 Evidence Freshness

Verification results are valid only for their bound candidate snapshot and relevant configuration/policy/tool schema identities. Any semantic candidate mutation invalidates them unless the check contract explicitly declares and mechanically proves independence from the changed surface.

### 9.15.6 Independent Intent Review

The reviewer MUST NOT receive hidden/private chain-of-thought. It receives:

* Goal/Change contracts;
* acceptance criteria;
* candidate diff/state evidence;
* relevant verification artifacts;
* a context compilation that does not simply reuse the implementer's unsupported conclusions.

Reviewer route/model identity and independent-context digest are recorded. If the required reviewer is unavailable, the result is `INCONCLUSIVE`/blocked according to policy, not success.

### 9.15.7 READY_FOR_USER Gate

`READY_FOR_USER` requires:

1. exact current CandidateSnapshot;
2. all mandatory focused/broad/structural checks resolved according to plan;
3. every mandatory acceptance criterion mapped to current evidence;
4. required intent review PASS;
5. no unresolved policy/identity corruption condition;
6. EvidenceManifest digest persisted.

### 9.15.8 ACCEPTED Gate

`ACCEPTED` additionally requires destination reconciliation, successful selected integration strategy, landed destination identity, and all mandatory post-integration checks resolved successfully under the plan.

---

## 9.16 Contract 13 — `CLIProtocol v1`

### 9.16.1 Command Surface

The required v1 command families are:

```text
harness doctor
harness run
harness status
harness resume
harness accept
harness reject
harness inspect
harness config validate
harness contracts check
```

Additional subcommands may be added compatibly. Removing or repurposing a command requires a major CLI contract version.

### 9.16.2 Human vs Machine Output

Interactive mode may use Rich/TUI rendering. Machine mode is enabled by `--json` and MUST obey:

* stdout contains exactly one final JSON result envelope unless a documented JSONL streaming submode is selected;
* diagnostics, progress, and human formatting go to stderr;
* ANSI escape sequences are forbidden on machine stdout;
* secret redaction applies before either stream;
* the JSON schema is versioned.

### 9.16.3 Result Envelope

```text
protocol: "harness.cli"
protocol_version: 1
command: string
status: SUCCESS | INVALID | APPROVAL_REQUIRED | POLICY_DENIED | VERIFICATION_FAILED |
        INCONCLUSIVE | CORRUPT | INTEGRATION_CONFLICT | INTERRUPTED |
        UNSUPPORTED | EXTERNAL_FAILURE | INTERNAL_FAILURE
symbolic_code: stable string
run_id: RunId | null
state: State | null
message: redacted human-readable string
data: strict command-specific object | null
```

### 9.16.4 Exit Classes

Exit codes are exactly the classes defined in §3.13:

```text
0  success
2  invalid usage/config
3  approval unavailable
4  policy denied
5  verification failed
6  unverifiable/inconclusive gate
7  persistence/repository corruption
8  integration conflict
9  interrupted/cancelled
10 unsupported capability/environment
11 provider/external integration failure
12 internal harness failure
```

Symbolic result codes provide finer detail; scripts SHOULD branch on symbolic codes when available and MAY branch on exit class for coarse behavior.

### 9.16.5 Headless Semantics

Headless mode MUST never wait for interactive input. If an operation requires unresolved approval or user-resolvable ambiguity, return the appropriate symbolic result and exit class immediately after durable state is safely checkpointed.

### 9.16.6 Cancellation

SIGINT/console cancellation requests a controlled interruption. The CLI attempts to reach a durable checkpoint, records `run.interrupted`, and exits 9. If durable-state safety cannot be proven, the run enters `RECOVERY_REQUIRED` before exit when persistence remains available.

---

## 9.17 Required Golden Conformance Suite

Before Phase 0 closes, the repository MUST contain a contract test suite that can run without a model provider or network connection.

Minimum fixture groups:

```text
contracts/tests/
├── serialization/
│   ├── valid_vectors.jsonl
│   └── invalid_vectors.jsonl
├── domain/
├── state_machine/
├── configuration/
├── events/
├── policy/
├── repository_identity/
├── tools/
├── verification/
├── persistence/
├── cli/
└── cross_contract/
```

The suite MUST prove at minimum:

* canonical digests are byte-stable;
* every registered domain object rejects malformed/unknown fields;
* every state transition is either explicitly valid or explicitly rejected;
* alias/config precedence does not widen security authority;
* unknown effects/resources/events fail closed;
* event and state mutation atomicity holds under injected failures;
* path traversal/symlink fixtures cannot escape the worktree;
* stale patch preimages result in zero mutation;
* approval requests cannot be reused after material request changes;
* candidate mutation invalidates bound evidence;
* `READY_FOR_USER` and `ACCEPTED` cannot be reached without their required proof;
* machine-mode CLI stdout conforms exactly to its JSON schema and exit class;
* no seeded secret fixture appears in ordinary persisted events/logs/output.

### 9.17.1 Independent Cross-Implementation Serialization Test

Because serialization sits beneath every other identity contract, its golden fixture generation MUST be validated by two independently written implementations or one implementation plus an external standards-oriented verifier. They must agree on exact bytes before new vectors are frozen.

---

## 9.18 Explicitly Deferred Behavior

The appendix intentionally does **not** freeze the following until the architecture's existing research gates are completed:

* exact minimum supported Git version;
* exact devcontainer feature subset;
* Docker/Podman platform-specific isolation behavior;
* scoped-network backend implementation;
* current provider request/stream/tool/continuation semantics;
* tokenizer/pricing APIs;
* Tree-sitter language matrix;
* OS-specific stale-lock proof;
* MCP protocol/SDK behavior;
* OpenTelemetry exporter behavior;
* GitHub Actions trust/token behavior;
* Phase-10 memory and third-party skill trust semantics beyond the already stated constraints.

For each deferred item, absence of a completed research decision means the corresponding capability is unsupported or blocked. It is not permission for the implementing agent to select a behavior silently.

---

## 9.19 Phase-0 Contract Closure Gate

Phase 0 is complete only when all of the following are true:

1. `ProductManifest v1`, `CanonicalSerialization v1`, `SemanticTypes v1`, `DomainSchemas v1`, `ReasonCodeRegistry v1`, `CrossContractInvariantRegistry v1`, `StateMachine v1`, `RecoveryProtocol v1`, `ConfigurationSchema v1`, `EventRegistry v1`, `ResourceNormalization v1`, `VerificationProtocol v1`, `CLIProtocol v1`, and `ResearchRegister v1` exist in machine-readable form.
2. The Phase-1-critical portions of `PersistenceSchema v1`, `SideEffectTransactionProtocol v1`, `PolicyContract v1`, and `RepositoryIdentity v1` are frozen sufficiently to prevent incompatible foundations.
3. Tool and verification envelope schemas are frozen even if later phases add specific tool/check implementations.
4. Every canonical registry has exactly one authoritative machine-readable source.
5. The golden conformance suite passes offline.
6. Generated/runtime Python definitions are mechanically proven consistent with their contracts.
7. No TODO, placeholder, “implementation-defined,” or prose-only ambiguity remains for any identity-, security-, state-, persistence-, approval-, evidence-, or CLI-success semantic required by Phase 0 or Phase 1.
8. Any unresolved version-sensitive dependency has an explicit `UNSUPPORTED`/`BLOCKED_CAPABILITY` behavior rather than a guessed fallback.

The implementation posture after this gate is therefore:

```text
load normative contracts
-> generate/implement primitives
-> run contract conformance
-> compose subsystems
-> verify cross-contract invariants
-> proceed to phase-specific behavior
```

A coding agent MAY choose internal module decomposition, helper names, private algorithms, indexes, caches, and performance optimizations where those choices do not alter a contract. It MUST NOT redefine identity, authority, success, failure, persistence, or evidence semantics while implementing them.

### 9.19.1 Definition of Implementation Determinacy

The blueprint is implementation-determinate for a phase when a competent coding agent starting from an empty repository can answer each of the following from committed contracts without inventing architecture:

```text
What object am I building?
What fields and types are legal?
What exact bytes identify it?
What transitions may occur?
Who has authority to permit the operation?
What resources/effects are authorized?
What is committed transactionally?
What event must be emitted?
What evidence proves success?
What invalidates that evidence?
What exact machine-visible result is returned on failure?
What behavior is intentionally unsupported?
```

If any answer affecting correctness, security, durable identity, or external machine behavior is “the implementer decides,” the relevant phase contract is not closed.

---

# 10. Implementation Closure Appendix v1.1

## 10.1 Closure Objective

This appendix closes the remaining implementation-significant gaps identified after the first Implementation Contract Edition. It does not revise the architecture. It supplies the missing semantic registries, exact machine contracts, recovery relations, side-effect transaction rules, resource normalization rules, and research-governance records required to make Phase 0 an implementation phase rather than an architecture phase.

The governing rule is:

> A behavior that affects correctness, security, durable identity, replay, recovery, evidence, approval reuse, or machine-visible output MUST be either explicitly defined by a normative contract or explicitly recorded as an unsupported/version-sensitive capability. It MUST NOT be silently selected by implementation code.

The new normative artifacts are:

```text
SemanticTypes v1
ReasonCodeRegistry v1
RecoveryProtocol v1
ResourceNormalization v1
SideEffectTransactionProtocol v1
ResearchRegister v1
```

The existing `DomainSchemas`, `ConfigurationSchema`, `EventRegistry`, `RepositoryIdentity`, `ToolProtocol`, `VerificationProtocol`, `PersistenceSchema`, and `CLIProtocol` contracts are strengthened below.

---

## 10.2 Build and Contract Representation Closure

### 10.2.1 Python Build System

The canonical v1 packaging decisions are:

```yaml
build_backend: hatchling
project_metadata_source: pyproject.toml
version_source: agentic_harness.__about__.__version__
lock_manager: uv
canonical_lockfile: uv.lock
editable_install: uv sync
build_command: uv build
unit_test_command: uv run pytest
```

Rules:

* `pyproject.toml` is the sole human-authored source for project metadata except the version string.
* The version string is owned by `agentic_harness.__about__.__version__`; build metadata reads it dynamically.
* `uv.lock` is committed and is the canonical development/CI resolution for supported platforms.
* Poetry/PDM/setuptools lock state MUST NOT coexist as a second authoritative dependency resolution.
* Release artifacts MUST be reproducible from a clean checkout plus the committed lockfile and declared build tool version.

### 10.2.2 Schema Languages

Normative JSON Schemas use **JSON Schema Draft 2020-12**.

Normative YAML files are data instances whose schema is either:

1. an adjacent JSON Schema Draft 2020-12 document; or
2. a JSON-Schema definition inside `contracts/meta/` referenced by stable `$id`.

Every normative schema MUST contain:

```text
$schema
$id
x-contract-name
x-contract-version
additionalProperties: false   # unless an explicit extension point is documented
```

Schema documents themselves are canonicalized under `CanonicalSerialization v1` after removing non-semantic presentation fields explicitly listed in `contracts/meta/schema_digest_exclusions.yaml`. `$comment`, indentation, and key insertion order do not affect schema identity; semantic keywords do.

---

## 10.3 `SemanticTypes v1`

`contracts/semantic_types.schema.json` is the only authoritative registry for shared scalar, identifier, nested, and discriminated-union types referenced across contracts.

### 10.3.1 Core Scalar Types

```text
Digest            := "sha256:" + 64 lowercase hex
GitOid            := algorithm-tagged lowercase hex: "sha1:<40>" | "sha256:<64>"
ContractVersion   := positive integer
RunVersion        := non-negative integer
SchemaVersion     := positive integer
UtcTimestamp      := canonical UTC timestamp from CanonicalSerialization v1
CanonicalPath     := normalized repo-relative POSIX path, no leading slash, no `.` or `..`
NonEmptyString    := Unicode scalar sequence length >= 1
ReasonCode        := registry-backed symbolic identifier
SymbolicCode      := registry-backed CLI identifier
```

Raw, untagged Git object IDs MUST NOT cross a durable contract boundary.

### 10.3.2 Identifier Types

All harness-owned IDs are UUIDv7 strings in lowercase canonical hyphenated form:

```text
RunId GoalId GoalRevisionId ChangeId ChangeRevisionId PlanId CheckId
ArtifactId EventId ToolCallId ModelCallId ApprovalId WorkPackageId
CheckpointId IntegrationId ReviewId ExperimentId
```

UUIDv7 generation MUST be implemented by a harness-owned generator conforming to RFC 9562 semantics so Python-version differences do not alter durable identity. The generator MUST:

* use millisecond Unix time in the timestamp field;
* use cryptographically secure randomness for random fields;
* preserve valid UUIDv7 bit layout;
* tolerate clock rollback without generating malformed UUIDs;
* not claim global monotonic ordering beyond the timestamp/random ordering provided by UUIDv7.

Ordering by UUID is never used as an authority or causality proof; explicit sequence fields serve that purpose.

### 10.3.3 `AcceptanceCriterion`

```text
criterion_id: string                  # stable within Goal revision
text: NonEmptyString
mandatory: bool = true
verification_class: BEHAVIORAL | REGRESSION | STRUCTURAL | INTENT | POST_INTEGRATION
source: USER | DERIVED
source_ref: string | null
success_semantics: EvidenceRequirement
```

`criterion_id` is unique within one Goal revision. A revised criterion that materially changes meaning requires a new Goal revision; reusing the same local `criterion_id` across revisions is permitted only when semantics are unchanged.

### 10.3.4 `EvidenceRequirement`

```text
mode: ALL | ANY | THRESHOLD
claim_refs: ordered non-empty list[EvidenceClaimRef]
threshold: integer | null
allow_waiver: bool = false
```

`THRESHOLD` requires `1 <= threshold <= len(claim_refs)`. `ALL` and `ANY` require `threshold = null`.

### 10.3.5 `Uncertainty`

```text
uncertainty_id: string
question: NonEmptyString
resolution_class: DETERMINISTIC | REPOSITORY_RESOLVABLE | USER_RESOLVABLE | EXTERNAL_RESEARCH
status: OPEN | RESOLVED | BLOCKED
resolution: string | null
resolution_evidence: ordered list[Digest]
blocking: bool
```

A blocking `USER_RESOLVABLE` uncertainty prevents plan finalization. A blocking `EXTERNAL_RESEARCH` uncertainty prevents enabling the dependent capability until a current ResearchRecord resolves it.

### 10.3.6 Evidence Types

```text
EvidenceClaim:
  claim_id: string
  proposition: NonEmptyString
  criterion_refs: ordered list[string]
  required_evidence_kinds: set[CHECK_RESULT | REPOSITORY_FACT | ARTIFACT | REVIEW]

CriterionEvidence:
  criterion_id: string
  claim_refs: ordered list[string]
  evidence_refs: ordered list[EvidenceRef]
  evaluation: SATISFIED | UNSATISFIED | INCONCLUSIVE | WAIVED
  evaluator_version: string

EvidenceRef:
  kind: VERIFICATION_RESULT | ARTIFACT | REPOSITORY_FACT | REVIEW_RESULT | WAIVER
  digest: Digest
  candidate_snapshot: Digest | null

CriterionReview:
  criterion_id: string
  status: PASS | FAIL | INCONCLUSIVE
  rationale_artifact_id: ArtifactId
  evidence_refs: ordered list[EvidenceRef]
```

### 10.3.7 `Waiver`

```text
waiver_id: UUIDv7
scope: CHECK | CLAIM | CRITERION
scope_ref: string
reason: NonEmptyString
issued_by: USER | TRUSTED_CI
issued_at: UtcTimestamp
expires_at: UtcTimestamp | null
bound_candidate: Digest | null
bound_change_revision: ChangeRevisionId
policy_rule_id: string
```

A waiver changes gate requirements; it never changes a check status to `PASS`.

### 10.3.8 Data Classification and Taint

Canonical classification order:

```text
PUBLIC < INTERNAL < SENSITIVE < SECRET
```

Taint is an independent set:

```text
SECRET_DERIVED
USER_PRIVATE
REPOSITORY_UNTRUSTED
EXTERNAL_UNTRUSTED
MODEL_GENERATED
TOOL_OUTPUT_UNTRUSTED
```

Derived content receives `max(classification(inputs))` and the union of input taints unless an explicit declassification rule authorized by policy applies. V1 defines **no automatic secret declassification rule**.

### 10.3.9 Inline-or-Artifact Value

```text
InlineTextOrArtifact =
  {kind: INLINE, text: string, encoding: UTF8}
  | {kind: ARTIFACT, artifact_id: ArtifactId, digest: Digest, media_type: string}
```

Inline payload limits are configured but MUST NOT exceed the contract maximum of 1 MiB. Larger payloads are artifactized.

### 10.3.10 `WorkPackage`

```text
work_package_id: WorkPackageId
parent_run_id: RunId
parent_change_revision: ChangeRevisionId
base_candidate_snapshot: Digest
objective: NonEmptyString
allowed_paths: ordered list[ResourcePattern]
allowed_effects: set[Effect]
acceptance_criteria: ordered list[string]
context_artifacts: ordered list[ArtifactId]
budget: {max_tokens:int|null, max_cost_usd:Decimal|null, max_tool_calls:int|null}
child_depth: 1
created_at: UtcTimestamp
digest: Digest
```

A child result is a `ChildResult` containing a commit OID or patch artifact plus evidence; the child MUST NOT mutate parent authoritative state directly.

---

## 10.4 Canonical Serialization Closure

The following rules supplement `CanonicalSerialization v1` and are identity-bearing.

### 10.4.1 Strings and Unicode

* Inputs MUST decode as valid Unicode scalar values. Lone UTF-16 surrogates and invalid UTF-8 are rejected before canonicalization.
* Unicode normalization is **not performed**. Distinct Unicode scalar sequences remain distinct identities.
* JSON escaping MUST use the shortest valid JSON representation required by the serializer: quotation mark, reverse solidus, and U+0000–U+001F controls are escaped; `/`, U+2028, and U+2029 are emitted as UTF-8 characters rather than gratuitously escaped.
* Canonical bytes are UTF-8 without BOM.

### 10.4.2 Datetime

* Naive datetimes are invalid.
* Inputs with offsets are converted to UTC before serialization.
* Canonical form is `YYYY-MM-DDTHH:MM:SS[.ffffff]Z`.
* Fractional seconds are omitted when zero; otherwise exactly six digits are emitted.
* Leap-second syntax (`:60`) is invalid in v1.
* Years outside Python's supported `datetime` range are invalid.

### 10.4.3 Decimal

* NaN, signaling NaN, positive/negative infinity are invalid.
* Signed zero canonicalizes to `0`.
* Scientific notation is not emitted.
* Trailing fractional zeros are removed.
* The decimal point is removed when the fractional component becomes empty.
* Canonicalization is independent of ambient Decimal context precision; inputs are serialized from their exact coefficient/exponent representation.
* Implementations MUST enforce a configurable resource limit on input digit count; exceeding it is `INVALID_CONTRACT_VALUE`, not truncation.

### 10.4.4 Maps, Sets, and Null

* Object keys are strings and sort by raw UTF-8 byte sequence after validation.
* Sets serialize as arrays sorted by each element's canonical serialized byte sequence.
* `null` is retained when the schema field is present and nullable.
* Omitted and explicit-null fields are distinct unless the schema declares a deterministic default and the object's identity profile explicitly says defaults are materialized before hashing.

### 10.4.5 Golden Edge Vectors

Golden vectors MUST include control characters, backslashes, quotes, `/`, U+2028/U+2029, composed/decomposed Unicode, very large Decimal magnitude/scale, signed zero, timezone offsets, zero/nonzero microseconds, empty containers, nested sets, and invalid surrogate input.

---

## 10.5 `ReasonCodeRegistry v1`

`contracts/reason_code_registry.yaml` is the sole registry for machine-stable reason codes. Codes are append-only within a major contract version.

Namespaces:

```text
CONFIG_*       configuration/contract validation
STATE_*        lifecycle/transition
POLICY_*       authorization/approval
RESOURCE_*     normalization/scope
REPO_*         repository/worktree identity
TOOL_*         tool protocol/execution
VERIFY_*       verification/evidence
RECOVERY_*     resume/reconciliation
PERSIST_*      database/artifact durability
PROVIDER_*     model/provider gateway
SANDBOX_*      environment/isolation
CLI_*          command-level machine result
INTERNAL_*     invariant/internal failure
```

Minimum required codes include:

```text
CONFIG_INVALID
CONFIG_UNKNOWN_KEY
CONFIG_ALIAS_CONFLICT
STATE_INVALID_TRANSITION
STATE_STALE_RUN_VERSION
POLICY_DENIED
POLICY_APPROVAL_REQUIRED
POLICY_APPROVAL_EXPIRED
POLICY_APPROVAL_CONSUMED
RESOURCE_INVALID
RESOURCE_SCOPE_WIDENING
REPO_IDENTITY_MISMATCH
REPO_DIRTY_DESTINATION
REPO_UNSUPPORTED_STATE
TOOL_INVALID_REQUEST
TOOL_STALE_PREIMAGE
TOOL_TIMEOUT
TOOL_CANCELLED
TOOL_PARTIAL_EFFECT_RECONCILIATION_REQUIRED
VERIFY_FAILED
VERIFY_INCONCLUSIVE
VERIFY_STALE_EVIDENCE
VERIFY_WAIVER_REQUIRED
RECOVERY_EXTERNAL_DRIFT
RECOVERY_AMBIGUOUS_EFFECT
PERSIST_CORRUPT
PERSIST_MIGRATION_REQUIRED
SANDBOX_UNENFORCEABLE_SCOPE
CLI_APPROVAL_UNAVAILABLE
CLI_UNSUPPORTED_CAPABILITY
INTERNAL_INVARIANT_VIOLATION
```

Every non-success CLI envelope MUST carry a registered code. Tool and policy records MUST use registered codes rather than arbitrary free-form strings for machine behavior.

---

## 10.6 Configuration Closure

### 10.6.1 Canonical File Locations

System, user, repository, and explicit configuration locations are:

```text
Linux system:     /etc/agentic-harness/config.toml
Linux user:       $XDG_CONFIG_HOME/agentic-harness/config.toml
                  fallback ~/.config/agentic-harness/config.toml
macOS system:     /Library/Application Support/Agentic Harness/config.toml
macOS user:       ~/Library/Application Support/Agentic Harness/config.toml
Windows system:   %PROGRAMDATA%\AgenticHarness\config.toml
Windows user:     %APPDATA%\AgenticHarness\config.toml
Repository:       <repo-root>/.harness/config.toml
Explicit:         --config <path>
```

A missing implicit config file contributes no values and is not an error. A missing explicit `--config` path is `CONFIG_INVALID`.

Repository configuration is classified `PROJECT_POLICY`; it may narrow but MUST NOT widen system/user security policy. Repository config is parsed as untrusted input before its values are admitted under the security-intersection rules.

### 10.6.2 Environment Overrides

Environment variables are disabled by default except this registry:

```text
HARNESS_CONFIG                  explicit config path equivalent
HARNESS_LOG_LEVEL               runtime.log_level
HARNESS_JSON                    runtime.machine_output
HARNESS_PROVIDER_OPENAI_KEY     secret broker reference only
HARNESS_PROVIDER_ANTHROPIC_KEY  secret broker reference only
HARNESS_PROVIDER_OPENROUTER_KEY secret broker reference only
```

Secret environment variables are never copied into canonical configuration values or configuration digests; the digest records secret-presence/reference identity, not secret plaintext.

### 10.6.3 Complete v1 Top-Level Schema Rule

Every top-level section named in §3.13 MUST have an explicit object schema before Phase 0 closes. A section with no enabled v1 functionality MUST still have a strict empty/disabled schema, for example:

```json
{"type":"object","properties":{"enabled":{"type":"boolean","default":false}},"additionalProperties":false}
```

No top-level section may remain an unconstrained `dict[str, Any]` extension point.

The canonical v1 minimum fields are:

```text
runtime:          machine_output, log_level, max_run_seconds
workspace:        root, preserve_on_failure
sandbox:          backend, require_isolation, cpu_limit, memory_limit_mb, pids_limit
policy:           policy_files, default_decision
providers:        named provider definitions with adapter/type and secret refs
routes:           primary, low_cost_candidates, stronger_candidates, reviewer
context:          max_input_tokens, max_artifact_inline_bytes
retrieval:        lexical, structural, trajectory, semantic flags
verification:     focused_required, broad_required, structural_required, intent_review_required
repository_commands: explicit named deterministic command specs
network:          mode, allowed_origins
 data_egress:     maximum_classification, destination rules
secrets:          named secret references only
parsers:          enabled parser IDs
memory:           enabled=false in v1 until Phase 10
skills:           enabled=false in v1 until Phase 10
 events:          jsonl_projection, projection_path
telemetry:        enabled, exporter=none in base v1
retention:        event_days, artifact_days, failed_run_days
approvals:        mode, grant_ttl_seconds
acceptance:       default_strategy
mcp:              enabled=false until Phase 11
 doctor:          strict
```

(The machine-readable schema, not this prose list, is authoritative; the prose list is the minimum closure requirement.)

---

## 10.7 Event Payload and Causality Closure

Every `event_registry.yaml` entry MUST contain:

```text
event_type
payload_schema_ref
schema_version
replay_role: AUTHORITATIVE | AUDIT_ONLY | DERIVED
redaction_profile
allowed_states
causation_rule
```

The common envelope is:

```text
event_id: EventId
run_id: RunId
sequence: integer >= 1
occurred_at: UtcTimestamp
event_type: registry value
event_version: integer
correlation_id: UUIDv7
causation_event_id: EventId | null
actor: RUNTIME | USER | TRUSTED_CI | MODEL | TOOL | SUBAGENT | EXTERNAL
payload: strict event-specific object
```

Causality rules:

* The first event of a run has `causation_event_id = null` and establishes `correlation_id = run_id` encoded as a UUID string.
* A state transition caused by a command references the command/request event.
* A tool result references the corresponding tool-request event.
* An approval grant/denial references the approval-request event.
* A child/subagent event stream uses the parent run correlation ID and its dispatch event as the first causation root.
* Events derived solely from database replay preserve original event IDs and MUST NOT be re-emitted as new authoritative events.

At Phase 0, every registered event name MUST have a concrete payload schema. Placeholder `{}` payloads are forbidden.

---

## 10.8 `RecoveryProtocol v1`

`state_machine.yaml` MUST contain `recovery_transitions` in addition to forward transitions.

### 10.8.1 Recovery Plan Schema

```text
RecoveryPlan:
  recovery_plan_id: UUIDv7
  run_id: RunId
  source_state: BLOCKED | INTERRUPTED | RECOVERY_REQUIRED | RECONCILIATION_REQUIRED | INTEGRATION_CONFLICT
  target_state: State
  required_proofs: ordered list[RecoveryProof]
  invalidations: ordered list[InvalidationRule]
  operator_action_required: bool
  created_at: UtcTimestamp
  digest: Digest
```

`RecoveryProof` is a discriminated union for repository identity, worktree identity, destination identity, config/policy identity, side-effect journal status, lock ownership, or explicit operator disposition.

### 10.8.2 Canonical Recovery Relation

```text
BLOCKED
  -> recorded pre-block state
     only when blocker reason is no longer true and all pre-block guards revalidate

INTERRUPTED
  -> recorded interruption checkpoint state
     only when process/tool tree is proven quiescent and identities still match

RECOVERY_REQUIRED
  -> last proven safe checkpoint state
     only after every incomplete side-effect transaction is classified APPLIED, NOT_APPLIED,
     or reconciled by its family-specific protocol

RECONCILIATION_REQUIRED
  -> recorded pre-drift state
     only after operator/runtime creates a new reconciled snapshot and explicitly invalidates stale evidence

INTEGRATION_CONFLICT
  -> READY_FOR_USER
     if integration attempt left destination unchanged and candidate remains valid
  -> IMPLEMENTING
     if conflict resolution creates a new candidate
  -> REJECTED
     on authorized abandonment
```

No recovery transition may target `ACCEPTED` directly.

### 10.8.3 Resume Idempotency

Calling `resume` when the run is already active is `STATE_INVALID_TRANSITION`. Calling `resume` repeatedly while still blocked returns the same blocker classification and MUST NOT duplicate external effects.

---

## 10.9 Repository Identity Closure

### 10.9.1 Path and Entry Encoding

Repository manifests use Git-style path bytes as the source of truth. Durable JSON representation encodes path bytes as UTF-8 only when valid; otherwise it uses URL-safe base64 with an explicit discriminator. Platform-decoded display strings are never identity-bearing.

Every tracked manifest entry contains:

```text
path_bytes
stage: 0|1|2|3
mode: 100644|100755|120000|160000
object_oid: GitOid | null
working_blob_digest: Digest | null
status_flags
```

Timestamps are excluded from identity.

### 10.9.2 Snapshot Component Algorithms

```text
head_commit:
  tagged GitOid or null for unborn HEAD

index_digest:
  SHA-256 of canonical ordered list of all index entries including stages 1/2/3,
  intent-to-add state, mode, path bytes, and object IDs

tracked_worktree_digest:
  SHA-256 of canonical ordered list of stage-0 tracked paths and the exact bytes currently
  materialized in the worktree, plus mode/symlink type

untracked_manifest_digest:
  SHA-256 of canonical ordered list of all included untracked path bytes, entry type,
  mode where meaningful, and exact-content SHA-256

submodule_manifest_digest:
  SHA-256 of canonical ordered list of gitlink path, recorded gitlink OID, initialized flag,
  nested HEAD OID when available, and nested dirty classification

repository_snapshot_digest:
  digest of repository format/object algorithm + head + all component digests + sparse-checkout identity
```

CRLF transformations matter to `tracked_worktree_digest` because it hashes materialized bytes. Git-normalized blob identity remains separately visible through index/object OIDs.

Renames have no special identity form; identity is state-based, not diff-based. A staged rename is represented by resulting index entries.

Case-colliding paths that cannot be materialized distinctly on the active platform produce `REPO_UNSUPPORTED_STATE` rather than lossy normalization.

### 10.9.3 Sparse Checkout

Snapshot identity includes whether sparse checkout is enabled, cone/non-cone mode, and the canonical digest of sparse patterns. A snapshot captured under one sparse definition is not equivalent to the same HEAD under another.

### 10.9.4 Submodules

The parent snapshot always binds the gitlink OID. If a submodule is initialized, nested HEAD and dirty classification are also recorded. V1 does not recursively govern submodule mutation unless a ChangeContract explicitly includes the submodule as a separately governed repository resource.

### 10.9.5 Golden Repository Fixtures

Required fixtures:

```text
clean
modified
staged
partially_staged
untracked
ignored
symlink
executable_bit
rename
deleted_staged
intent_to_add
merge_conflict
submodule_clean
submodule_dirty
detached_head
unborn_branch
sparse_checkout
non_utf8_path
case_collision_manifest
```

Each fixture MUST freeze every snapshot component and final digest.

### 10.9.6 Dirty-State Materialization

Dirty-state reconstruction into an isolated worktree MUST use a two-layer procedure:

1. materialize the committed base using Git worktree plumbing;
2. replay a harness-generated `WorkspaceOverlay` containing index-stage state plus exact working/untracked bytes.

After replay, the harness recomputes the full snapshot and requires equality with the source snapshot except for explicitly non-identity metadata. If equality cannot be achieved, the run blocks; it MUST NOT continue on an approximate reconstruction.

---

## 10.10 `ResourceNormalization v1`

Resource authorization uses typed structured resources. Free-form resource strings are forbidden at policy boundaries.

### 10.10.1 Resource Pattern Grammar

A `ResourcePattern` is:

```text
kind: ResourceKind
match: EXACT | PREFIX | GLOB
value: kind-specific canonical structure
```

Regex matching is not supported in v1 policy patterns. `PREFIX` is permitted only for hierarchical kinds (`repo_path`, `artifact_namespace`, `external_service_path`). Glob syntax is the harness-defined path glob (`*`, `?`, `**`) applied after canonical normalization; it is never delegated to a shell.

### 10.10.2 Normalized Resource Kinds

```text
repo_path
process
network_origin
external_service
secret
repository_ref
artifact
```

#### `repo_path`

Canonical repo-relative POSIX path after lexical normalization and symlink-safe resolution against the governed worktree. Authorization applies to both lexical requested path and resolved target; either outside scope denies.

#### `process`

```text
executable: canonical absolute executable path
argv: ordered exact argument vector
cwd: canonical repo/workspace path
script: canonical path or null when interpreter-style invocation is detected
env_keys: sorted names of environment variables exposed
```

Approval reuse compares the full normalized process resource plus argument digest.

#### `network_origin`

```text
scheme: lowercase http | https
host_ascii: IDNA A-label lowercase or canonical IP literal
port: explicit integer after default-port materialization
```

Paths/query fragments are not part of origin. `https://example.com` and `https://example.com:443` normalize identically. A hostname and an IP literal do **not** normalize identically.

Redirects are new network resources and must independently pass policy. DNS resolution does not widen hostname authorization to arbitrary returned IPs; enforcement backends must mitigate rebinding according to the phase's researched backend contract. If they cannot, host-scoped network is unsupported.

#### `external_service`

```text
provider: stable adapter/server ID
operation: stable operation/tool name
account_scope: opaque configured account reference or null
resource_path: provider-defined canonical path or ID
```

#### `secret`

A secret resource is the configured secret identifier, never plaintext:

```text
secret_id
broker
purpose
```

#### `repository_ref`

```text
repo_identity: repository root identity
ref_kind: HEAD | BRANCH | TAG | FULL_REF | OBJECT
ref_name_or_oid: normalized exact value
```

#### `artifact`

```text
namespace
artifact_id | digest
media_type | null
```

### 10.10.3 Adversarial Vectors

Tests MUST cover path traversal, symlink/junction escape, case-fold collisions, Windows drive/UNC forms, IDNA, trailing dots, default ports, IPv4/IPv6 literals, redirects, process interpreter/script ambiguity, PATH shadowing, environment injection, and resource-pattern broadening.

---

## 10.11 Data Redaction Closure

V1 redaction combines deterministic structured redaction with exact-known-secret matching.

Redaction sources:

1. schema fields marked `x-sensitive: true`;
2. registered secret values held by the broker, matched exactly before persistence/egress;
3. registered credential formats required by enabled adapters.

Entropy-only secret detection is advisory and MUST NOT be the sole mechanism for classifying or redacting a value.

For transformed/encoded secret values, the broker may register deterministic derived representations (for example base64 of an exact secret) only when the transformation is explicitly supported. The harness MUST NOT attempt unbounded transformation guessing.

Redaction occurs before event persistence, tool-output persistence, model context admission, telemetry export, and CLI rendering.

---

## 10.12 Tool Registry Closure

`contracts/tool_protocol/registry.yaml` MUST enumerate every tool callable by an agent. Unregistered tools cannot be invoked.

Each entry contains:

```text
tool_name
tool_version
request_schema_ref
result_schema_ref
error_codes
effect_calculator
resource_calculator
atomicity: READ_ONLY | SINGLE_RESOURCE_ATOMIC | JOURNALED_MULTI_RESOURCE
cancellation_profile
output_limit_profile
```

### 10.12.1 V1 Filesystem Tools

Canonical tool names:

```text
fs.stat
fs.list
fs.read_bytes
fs.read_text
fs.write_file
fs.mkdir
fs.rename
fs.delete
```

All write-like filesystem tools require worktree-local normalized resources. `fs.read_text` requires explicit encoding (default UTF-8) and returns `TOOL_INVALID_ENCODING` rather than lossy replacement unless the caller explicitly requests a replacement policy allowed by schema.

### 10.12.2 Search Tools

```text
search.literal
search.regex
search.glob
```

Searches operate only on authorized roots. Binary detection, encoding failure, maximum matches, and output byte limits are explicit request/result fields. Regex uses Python's standard `re` semantics in v1 and is a search mechanism, not a policy matcher.

### 10.12.3 Patch Representation

V1 uses a structured `PatchSet`, not a shell-fed patch command:

```text
PatchSet:
  base_snapshot: Digest
  operations: ordered list[
    CreateFile(path, bytes_digest, content_artifact),
    ModifyFile(path, preimage_digest, postimage_digest, content_artifact),
    DeleteFile(path, preimage_digest),
    RenameFile(from_path, to_path, preimage_digest, postimage_digest),
    SetExecutable(path, expected_mode, new_mode)
  ]
```

Binary file creation/modification remains unsupported in v1 unless the operation is byte-for-byte artifact materialization under an explicit binary-enabled tool capability. Text diff syntax may be accepted at UI boundaries but MUST compile to `PatchSet` before authorization/execution.

### 10.12.4 Process Execution

The normalized request contains exact executable, argv array, cwd, timeout, stdin source, environment allowlist, and expected output limit. `shell=false` is mandatory for the base process tool.

Sanitized default environment contains only values explicitly selected by the environment planner. At minimum it constructs controlled `PATH`, locale, temporary-directory variables, and required toolchain variables. Inherited host variables are deny-by-default. Provider/API secrets are never inherited into sandbox processes unless a separate secret capability explicitly authorizes exposure.

### 10.12.5 Git Tool Surface

Agent-callable Git operations are wrappers, not arbitrary `git` execution:

```text
git.status
git.diff
git.show
git.rev_parse
git.ls_files
git.add
git.commit
git.worktree_create
git.worktree_remove
git.apply_candidate_integration
```

Network-capable operations (`fetch`, `pull`, `push`, remote submodule update) are not exposed through the base Git tool in v1. Hooks and external filters are disabled or sanitized for harness-managed Git operations unless explicitly required and separately authorized.

---

## 10.13 `SideEffectTransactionProtocol v1`

SQLite cannot atomically commit filesystem, Git, process, or external effects. The harness therefore uses a durable intent/reconcile protocol rather than pretending cross-resource ACID exists.

### 10.13.1 Side-Effect Journal

Every non-read-only external effect has a `SideEffectTxn`:

```text
txn_id: UUIDv7
run_id: RunId
tool_call_id: ToolCallId
family: FILESYSTEM | GIT | PROCESS | EXTERNAL_WRITE | APPROVAL_CONSUMPTION
request_digest: Digest
pre_state_digest: Digest | null
phase: PREPARED | APPLYING | OBSERVED_APPLIED | COMMITTED | RECONCILIATION_REQUIRED | ABORTED
post_state_digest: Digest | null
created_at
updated_at
```

### 10.13.2 Execution Protocol

```text
1. validate + authorize request
2. BEGIN IMMEDIATE
3. persist PREPARED SideEffectTxn and reserve/consume required one-shot approval atomically
4. COMMIT SQLite
5. perform external effect
6. observe/recompute authoritative post-state
7. BEGIN IMMEDIATE
8. persist result + event + post-state and mark COMMITTED atomically
9. COMMIT SQLite
```

If the process dies between steps 4 and 8, resume MUST reconcile the durable intent against live state before any retry.

### 10.13.3 Retry Classification

On recovery each prepared transaction becomes exactly one of:

```text
NOT_APPLIED        safe to execute once
APPLIED_MATCH      effect occurred exactly as requested; commit observation without replay
APPLIED_DIVERGENT  some effect occurred but post-state differs; RECONCILIATION_REQUIRED
UNKNOWN            cannot establish whether effect occurred; RECOVERY_REQUIRED
```

Blind retries of `UNKNOWN` or `APPLIED_DIVERGENT` effects are forbidden.

### 10.13.4 Artifact Writes

CAS object installation uses write-temp -> fsync file -> atomic replace/link into digest path -> fsync containing directory where supported -> verify digest. An orphaned valid object is harmless and may be adopted by later reconciliation; an invalid object at a digest path is `PERSIST_CORRUPT`.

### 10.13.5 Integration

Git integration records the destination pre-state before mutation. After mutation, the destination identity is recomputed before the database marks integration complete. Crash after Git mutation but before DB commit is reconciled by comparing live destination identity with the candidate/integration intent; it is never automatically repeated.

---

## 10.14 Persistence DDL Closure

The committed `persistence.sql` MUST specify exact types, constraints, FKs, uniqueness, and indexes. V1 database pragmas are:

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = FULL;
PRAGMA busy_timeout = 5000;
```

Production may only weaken `synchronous` through a future explicit durability-profile contract; v1 has no such profile.

Required table separation includes at least:

```text
runs
goals
goal_revisions
changes
change_revisions
verification_plans
verification_results
evidence_manifests
approval_requests
approval_grants
approval_consumptions
events
artifacts
tool_calls
model_calls
checkpoints
integration_records
side_effect_txns
recovery_plans
locks
schema_migrations
```

`ApprovalRequest`, `ApprovalGrant`, and consumption are separate records. Mutable counters MUST NOT erase prior grant/consumption history.

All state-transition, revision, approval, and authoritative result mutations use `BEGIN IMMEDIATE` to serialize the single writer. Read-only inspection may use deferred read transactions.

Migration rules:

* migrations are numbered, append-only, checksum-bound SQL/Python steps;
* startup refuses a database newer than the runtime schema;
* irreversible migrations require pre-migration backup metadata and explicit major/minor release documentation;
* migration completion is transactional where SQLite permits; non-transactional filesystem migration work uses `SideEffectTransactionProtocol v1`.

---

## 10.15 Verification Evidence Algebra Closure

Verification is evaluated by a deterministic gate evaluator, not orchestration-specific conditionals.

### 10.15.1 Claim Evaluation

For each `EvidenceClaim`:

```text
ESTABLISHED      at least one permitted evidence path satisfies the claim and no mandatory
                 contradicting result remains current
DISPROVEN        a current mandatory result directly falsifies the claim
INCONCLUSIVE     required evidence is missing, errored, stale, or unresolved
WAIVED           an authorized current waiver covers the claim
```

One result MAY support multiple claims if its schema declares those claim refs. A repository fact MAY establish a claim without executing a check only when the claim's `required_evidence_kinds` permits `REPOSITORY_FACT`.

### 10.15.2 Criterion Evaluation

A criterion applies its `EvidenceRequirement` to claim states:

* `ALL`: every claim is `ESTABLISHED` or validly `WAIVED`.
* `ANY`: at least one claim is `ESTABLISHED`; waiver alone does not satisfy `ANY` unless the criterion explicitly permits full waiver.
* `THRESHOLD`: at least N claims are `ESTABLISHED`; waived claims count only when `allow_waiver=true`.

Any current `DISPROVEN` claim for a mandatory criterion makes the criterion `UNSATISFIED` unless an authorized waiver explicitly covers that claim class.

### 10.15.3 Check Mechanism Union

`VerificationCheckSpec.mechanism` is exactly one of:

```text
CommandCheck
PythonCallableCheck
JsonAssertionCheck
FileAssertionCheck
RepositoryInvariantCheck
ArtifactComparisonCheck
ReviewerCheck
```

Arbitrary eval expressions and shell predicate strings are forbidden.

### 10.15.4 Success Predicates

`CommandCheck` may evaluate exit-code sets plus bounded stdout/stderr assertions. Regex predicates use registered patterns and cannot execute code. `JsonAssertionCheck` uses a restricted JSON Pointer + comparator language (`equals`, `not_equals`, `exists`, `contains`, numeric comparisons). Custom Python verifiers must be registered code packaged with the harness/repository trust policy and are not loaded from untrusted generated text.

### 10.15.5 `NOT_APPLICABLE`

`NOT_APPLICABLE` requires a deterministic applicability predicate that evaluates false against the current candidate/configuration. A model statement that a check is irrelevant is insufficient.

### 10.15.6 Reviewer Independence

V1 independence requires:

* a fresh reviewer context that excludes implementing-agent hidden scratch state;
* no acceptance of the implementer's conclusion as evidence;
* criterion/evidence artifacts supplied independently from implementation narration;
* reviewer route may use the same provider/model family, but if configuration defines a distinct `routes.reviewer`, that configured route is mandatory.

Provider/model diversity is recommended but not required for v1 semantic independence.

### 10.15.7 Invalidation Dependency Set

Every check declares `identity_dependencies` chosen from:

```text
CANDIDATE_SNAPSHOT
CONFIG_DIGEST
POLICY_DIGEST
TOOL_SCHEMA_DIGEST
ENVIRONMENT_DIGEST
PROVIDER_ROUTE_DIGEST
DESTINATION_SNAPSHOT
```

A result remains current only while all declared dependencies equal their bound values. Candidate-mutating checks always depend on `CANDIDATE_SNAPSHOT`.

### 10.15.8 Post-Integration Reuse

Pre-integration evidence may remain usable after integration only for checks whose declared dependencies exclude destination identity and whose candidate tree digest exactly equals the landed destination tree digest. Checks that depend on worktree environment, destination metadata, hooks, integration mechanics, or post-landed behavior MUST rerun.

---

## 10.16 CLI Command Closure

The machine-visible v1 command signatures are:

```text
harness doctor [--json]
harness run <objective|--objective-file PATH> [--repo PATH] [--config PATH] [--json]
harness status <run-id> [--json]
harness resume <run-id> [--json]
harness accept <run-id> [--strategy squash|cherry-pick|fast-forward|patch-only] [--json]
harness reject <run-id> [--reason TEXT] [--json]
harness inspect <run-id> [--artifact ID] [--json]
harness config validate [PATH] [--json]
harness contracts check [--json]
```

`run` rejects simultaneous positional objective and `--objective-file`.

Command-specific `data` schemas are mandatory and stored under `contracts/cli_protocol/data/`. At minimum:

```text
doctor -> capability matrix + blockers
run -> run_id, state, goal_revision_id, blocker|null
status -> run summary, current identities, pending action
resume -> resulting state, recovered_from, blocker|null
accept -> strategy, candidate_snapshot, destination_before, destination_after|null
reject -> terminal state, reason artifact|null
inspect -> requested typed object/artifact references
config validate -> config_digest, sources, warnings
contracts check -> contract versions, fixture counts, failures
```

Idempotency:

* repeating `reject` on an already rejected run returns success with `CLI_ALREADY_REJECTED` and no new disposition effect;
* repeating `accept` on an already accepted run returns success only if the recorded landed destination identity still matches; otherwise `RECONCILIATION_REQUIRED`;
* repeating `accept` while `ACCEPTING` or in conflict does not start a second integration;
* repeating cancellation after `INTERRUPTED` is a no-op success;
* `resume` follows §10.8.3.

---

## 10.17 Agent-Loop and Retrieval Determinism Boundary

The following v1 defaults are frozen sufficiently to avoid ad-hoc agent behavior while leaving quality tuning experimental.

### 10.17.1 Anti-Thrashing

A Tier-1 repair loop stops and escalates/blocks when any occurs:

```text
same normalized failure signature after 2 materially distinct patches
3 consecutive candidate mutations without a newly passing required check
5 implementation attempts for one Change slice
configured tool/cost/token budget exhausted
```

A “materially distinct patch” means the candidate digest changed and at least one changed path or changed hunk differs from the previous failed candidate.

### 10.17.2 RIG Core Schema

The deterministic Repository Intelligence Graph v1 has node kinds:

```text
FILE DIRECTORY SYMBOL MANIFEST TEST CI_CONFIG INSTRUCTION COMMAND ARTIFACT
```

and edge kinds:

```text
CONTAINS DEFINES IMPORTS DEPENDS_ON TESTS REFERENCES CONFIGURES GENERATED_FROM
```

Each node/edge identity binds repository snapshot plus canonical source location. Unsupported languages may omit symbol edges but MUST still provide file/tree nodes.

### 10.17.3 Baseline Retrieval

Before experimental ranking is enabled, v1 retrieval is deterministic:

1. exact/path and user-mentioned identifier matches;
2. lexical search hits;
3. structural neighbors from RIG;
4. test/source and manifest/config relations;
5. current changed-file trajectory;
6. stable tie-break by canonical path/span.

RRF weights, learned ranking, embeddings, and semantic ranking remain experimental defaults and cannot alter security/authority behavior.

---

## 10.18 Platform/External Research Register v1

`contracts/research_register.yaml` distinguishes legitimate implementation-time research from missing architecture.

Each record is:

```text
research_id
capability
question
authoritative_sources_allowed
resolved_value | null
source_refs
observed_versions
verified_at
expires_at | null
recheck_trigger
failure_behavior: BLOCKED_CAPABILITY | UNSUPPORTED | DEGRADED_DECLARED
```

Initial required records:

```text
GIT_MIN_VERSION
GIT_WORKTREE_BEHAVIOR
GIT_SHA256_REPOSITORY_SUPPORT
GIT_SPARSE_CHECKOUT_BEHAVIOR
WINDOWS_GIT_FILEMODE_CASE_BEHAVIOR
PYTHON_SUPPORTED_SQLITE_MATRIX
FILESYSTEM_ATOMIC_REPLACE_AND_FSYNC
POSIX_PROCESS_GROUP_TERMINATION
WINDOWS_JOB_OBJECT_TERMINATION
DOCKER_PODMAN_ISOLATION
SCOPED_NETWORK_ENFORCEMENT
OPENAI_ADAPTER_SEMANTICS
ANTHROPIC_ADAPTER_SEMANTICS
OPENROUTER_ADAPTER_SEMANTICS
TOKEN_COUNTING_APIS
TREESITTER_SUPPORT_MATRIX
LOCK_OWNERSHIP_STALENESS
MCP_PROTOCOL_SDK
OTEL_PYTHON_EXPORTER
GITHUB_ACTIONS_TRUST_TOKEN
PACKAGE_INDEX_NAME_AVAILABILITY
```

A research record MUST cite primary/official documentation or empirical harness evidence. Secondary sources may guide investigation but cannot be the sole closure evidence for a safety- or compatibility-critical record.

---

## 10.19 Updated Contract-Conformance Suite

The Phase-0 offline suite is extended with:

```text
contracts/tests/
├── semantic_types/
├── reason_codes/
├── recovery/
├── resource_normalization/
├── side_effect_transactions/
├── repository_identity/golden_repos/
├── event_payloads/
├── cli_data_schemas/
└── research_register/
```

Required failure-injection scenarios include:

* crash after approval consumption but before side effect;
* crash after side effect but before result commit;
* crash after Git integration but before DB commit;
* orphan CAS object after rollback;
* symlink/junction swap between authorization and use;
* network redirect to a different origin;
* PATH shadowing and interpreter/script ambiguity;
* partially staged and conflict-stage repository states;
* stale evidence after candidate/config/policy/tool-schema mutation;
* repeated accept/reject/resume/cancel commands;
* unknown reason/event/tool/config fields.

---

## 10.20 Revised Phase-0 Exit Gate

Phase 0 MUST NOT close until:

1. all foundational/control contracts required by Phase 1 are complete, not merely named;
2. every shared/nested type referenced by another schema resolves through `SemanticTypes v1` or an explicit owning schema;
3. all durable records written in Phase 0/1 have complete schemas;
4. every v1 configuration section is strict and every override source is registered;
5. every registered event has a concrete payload schema and causality rule;
6. every machine-visible non-success path maps to a registered reason/symbolic code;
7. recovery transitions are machine-readable and all exceptional states have deterministic resume/disposition rules;
8. repository identity algorithms pass golden Git fixtures across supported platforms or the platform is explicitly unsupported;
9. resource normalization and policy matching pass adversarial fixtures;
10. every Phase-1/2 side-effect family has a journal/reconciliation rule before it can execute;
11. persistence DDL and durability pragmas are committed and migration-tested;
12. tool registry entries have concrete schemas/effect/resource calculators before invocation is possible;
13. verification claim/criterion/gate algebra is executable and property-tested;
14. CLI commands and `data` envelopes are schema-complete and idempotency-tested;
15. all remaining unresolved items are present in `ResearchRegister v1` with fail-closed behavior.

The operative boundary becomes:

```text
PHASE 0
  = close executable contracts + prove contract conformance

PHASE 1+
  = implement behavior against those contracts
```

A coding agent starting Phase 1 is therefore not authorized to invent:

```text
shared semantic types
schema dialects
serialization edge behavior
reason codes
config fields or override paths
event payloads or causality
recovery transitions
repository digest algorithms
resource-pattern syntax
resource normalization
classification/taint ordering
tool names or envelopes
patch semantics
cross-resource retry semantics
verification evidence algebra
CLI result shapes or idempotency
```

If a required answer is absent, implementation stops at `CONTRACT_UNRESOLVED`; it does not choose a plausible default.

---

## 10.21 Final Implementation-Determinacy Test

The blueprint is ready to hand to a blank-repository coding agent only when a contract-conformance command can answer, without model interpretation:

```text
harness contracts check --json
```

and prove:

```text
all referenced schema types resolve
all registries are unique and closed
all golden identities match
all state + recovery transitions are total over supported commands
all security resources normalize deterministically
all event payloads validate
all durable side effects are journaled/reconcilable
all evidence gates evaluate deterministically
all CLI machine outputs validate
all unresolved external facts are explicitly blocked or unsupported
```

At that point the implementation mandate is narrow and enforceable:

> **Implement the contracts. Do not invent architecture.**

