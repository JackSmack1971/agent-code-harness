"""`PolicyContract v1` reference implementation (Blueprint 3.7, 9.12, 10.11).

`contracts/policy_contract.schema.json` / `.yaml` is the sole authoritative
source for the closed Effect set, the Trust class list, the decision
algebra's dimensions/results/rules, approval-binding semantics, and the
redaction-source registry; this module is the executable decision
procedure those rules describe, not a second hand-maintained copy of the
rule text (Canonical Identity Rules). Resource normalization/matching is
`_resource_normalization.py`; secret/classification redaction is
`_classification.py`. Full runtime wiring into a sandboxed tool-execution
path is Phase 2/3 (`.claude/references/phase-registry.md`); what exists
here is the decidable decision algebra itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from ._contracts import find_contracts_root, load_yaml
from ._classification import ClassificationError, classification_rank, union_taint
from ._resource_normalization import matches_resource_pattern

REASON_CODE_POLICY_DENIED = "POLICY_DENIED"
REASON_CODE_POLICY_APPROVAL_REQUIRED = "POLICY_APPROVAL_REQUIRED"

EFFECTS: frozenset[str] = frozenset({
    "READ", "WORKSPACE_WRITE", "PROCESS_EXEC", "SHELL_INTERPRETATION", "NETWORK",
    "DATA_EGRESS", "EXTERNAL_READ", "EXTERNAL_WRITE", "SECRET_ACCESS", "DESTRUCTIVE", "PRIVILEGED",
})

TRUST_CLASSES: frozenset[str] = frozenset({
    "SYSTEM_TRUSTED", "USER_TRUSTED", "PROJECT_POLICY",
    "REPOSITORY_UNTRUSTED", "TOOL_OUTPUT_UNTRUSTED", "EXTERNAL_UNTRUSTED", "MODEL_GENERATED",
})

UNTRUSTED_TRUST_CLASSES: frozenset[str] = frozenset({
    "REPOSITORY_UNTRUSTED", "TOOL_OUTPUT_UNTRUSTED", "EXTERNAL_UNTRUSTED", "MODEL_GENERATED",
})

# 9.12.5 results, in ascending "how gated" order used to combine multiple matching rules.
DECISIONS: tuple[str, ...] = ("ALLOW", "APPROVAL_REQUIRED", "DENY", "BLOCKED_CAPABILITY")
_DECISION_SEVERITY = {name: rank for rank, name in enumerate(DECISIONS)}

_SPECIFICITY = {"EXACT": 2, "PREFIX": 1, "GLOB": 0}
_AUTHORITY_RANK = {"PROJECT_POLICY": 1, "USER_TRUSTED": 2, "SYSTEM_TRUSTED": 3}


class PolicyError(ValueError):
    def __init__(self, message: str, *, reason_code: str = REASON_CODE_POLICY_DENIED) -> None:
        super().__init__(message)
        self.reason_code = reason_code


@dataclass(frozen=True)
class PolicyRule:
    """One authority layer's rule for an effect over a resource pattern.

    `authority` is provenance metadata (3.7/9.12.4), used only to determine
    which rules apply, never as a scalar permission score: a rule from an
    untrusted authority can never grant anything (9.12.5/INV-SECURITY-002),
    it can only be considered at all when `authority` is not in
    `UNTRUSTED_TRUST_CLASSES`.
    """

    authority: str
    effect: str
    kind: str
    match: str
    value: str
    decision: str  # "ALLOW" | "DENY" | "APPROVAL_REQUIRED"


@dataclass(frozen=True)
class ApprovalGrantLike:
    disposition: str  # ALLOW_ONCE | ALLOW_RUN | DENY
    binding: dict[str, Any]
    consumed: bool
    expired: bool


@lru_cache(maxsize=8)
def load_policy_contract(contracts_root: Path | None = None) -> dict[str, Any]:
    """Load the authoritative PolicyContract registry on demand.

    Importing this module remains side-effect free; authorization itself is
    invalid without the canonical registry and therefore fails closed when it
    cannot be loaded.
    """
    root = contracts_root or find_contracts_root()
    if root is None:
        raise PolicyError("contracts/ root not found; policy authority is unavailable")
    return load_yaml(root / "policy_contract.yaml")


def _policy_sets(contracts_root: Path | None = None) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    doc = load_policy_contract(contracts_root)
    algebra = doc["decision_algebra"]
    return frozenset(doc["effects"]), frozenset(doc["trust_classes"]), frozenset(algebra["untrusted_trust_classes"])


def effect_is_known(effect: str, *, contracts_root: Path | None = None) -> bool:
    try:
        effects, _trust, _untrusted = _policy_sets(contracts_root)
    except (OSError, KeyError, TypeError, PolicyError):
        return False
    return effect in effects


RESOURCE_KINDS: frozenset[str] = frozenset({"repo_path", "process", "network_origin", "external_service", "secret", "repository_ref", "artifact"})


def resource_kind_is_known(kind: str, *, contracts_root: Path | None = None) -> bool:
    try:
        root = contracts_root or find_contracts_root()
        if root is None:
            return False
        doc = load_yaml(root / "resource_normalization.yaml")
        return kind in frozenset(doc["resource_kinds"])
    except (OSError, KeyError, TypeError):
        return False


def _matching_rules(effect: str, kind: str, normalized_key: str, rules: list[PolicyRule], *, contracts_root: Path | None = None) -> list[PolicyRule]:
    matched = []
    try:
        _effects, trust_classes, untrusted_classes = _policy_sets(contracts_root)
    except (OSError, KeyError, TypeError, PolicyError):
        return matched
    for rule in rules:
        if rule.authority not in trust_classes:
            # Unknown provenance is not trusted by default.  Treating a new or
            # misspelled class as trusted would turn registry drift into an
            # authority expansion.
            continue
        if rule.authority in untrusted_classes:
            # 9.12.5/INV-SECURITY-002: untrusted-authority rules never participate.
            continue
        if rule.effect not in _effects or rule.effect != effect:
            continue
        if rule.decision not in {"ALLOW", "APPROVAL_REQUIRED", "DENY"}:
            # Malformed policy is fail-closed, including a malformed rule that
            # happens to match the request.
            continue
        try:
            matches = matches_resource_pattern(kind=kind, match=rule.match, value=rule.value, normalized_key=normalized_key, pattern_kind=rule.kind)
        except (KeyError, ValueError):
            matches = False
        if not matches:
            continue
        matched.append(rule)
    return matched


def _combine(matched: list[PolicyRule]) -> str | None:
    """9.12.5: explicit deny wins; narrower scope wins over broader scope.

    Narrowest-specificity rule governs; among rules tied for narrowest
    specificity, DENY wins over APPROVAL_REQUIRED wins over ALLOW (fail
    toward the more conservative outcome on a genuine tie, never toward
    ALLOW).
    """
    if not matched:
        return None
    allows = [rule for rule in matched if rule.decision != "DENY"]
    denies = [rule for rule in matched if rule.decision == "DENY"]
    if denies and not allows:
        return "DENY"
    if denies:
        highest_allow_authority = max(_AUTHORITY_RANK.get(rule.authority, 0) for rule in allows)
        if any(_AUTHORITY_RANK.get(rule.authority, 0) >= highest_allow_authority for rule in denies):
            return "DENY"
    max_specificity = max(_SPECIFICITY[rule.match] for rule in matched)
    narrowest = [rule for rule in matched if _SPECIFICITY[rule.match] == max_specificity]
    return max((rule.decision for rule in narrowest), key=lambda d: _DECISION_SEVERITY[d])


def evaluate(
    *,
    effect: str,
    kind: str,
    normalized_key: str,
    rules: list[PolicyRule],
    sandbox_enforceable: bool = True,
    approval: ApprovalGrantLike | None = None,
    request_binding: dict[str, Any] | None = None,
    contracts_root: Path | None = None,
    data_classification: str | None = None,
    maximum_classification: str | None = None,
    taint: frozenset[str] | None = None,
) -> str:
    """Evaluate one (effect, normalized resource) pair against the decision algebra.

    Returns one of `DECISIONS`. Does not mutate/consume `approval`; callers
    perform ALLOW_ONCE consumption atomically immediately before the side
    effect begins (9.12.6), separately from this pure decision function.
    """
    if not effect_is_known(effect, contracts_root=contracts_root):
        return "DENY"
    if not resource_kind_is_known(kind, contracts_root=contracts_root):
        return "DENY"
    if taint is not None:
        try:
            union_taint(taint)
        except ClassificationError:
            return "DENY"
    if data_classification is not None and maximum_classification is not None:
        try:
            if classification_rank(data_classification) > classification_rank(maximum_classification):
                return "DENY"
        except ClassificationError:
            return "DENY"

    decision = _combine(_matching_rules(effect, kind, normalized_key, rules, contracts_root=contracts_root))
    if decision is None:
        # policy.default_decision (configuration_schema.yaml): fail closed.
        decision = "DENY"

    if decision == "DENY":
        return "DENY"

    if not sandbox_enforceable:
        # 9.12.5: unavailable enforcement yields BLOCKED_CAPABILITY, never an
        # implicit widening — this overrides ALLOW/APPROVAL_REQUIRED but
        # never a DENY (already returned above).
        return "BLOCKED_CAPABILITY"

    if decision == "ALLOW":
        return "ALLOW"

    # decision == "APPROVAL_REQUIRED"
    if approval is not None and _approval_satisfies(approval, request_binding):
        return "ALLOW"
    return "APPROVAL_REQUIRED"


def _approval_satisfies(approval: ApprovalGrantLike, request_binding: dict[str, Any] | None) -> bool:
    """9.12.6: an approval can satisfy only an approval requirement already
    permitted by policy; it cannot override a hard deny (enforced by the
    caller never reaching here when `decision == "DENY"`).
    """
    if approval.disposition == "DENY":
        return False
    if approval.consumed or approval.expired:
        return False
    # A grant without a request binding cannot prove what it authorizes.  Do
    # not let callers accidentally turn a missing binding into a wildcard.
    if request_binding is None or approval.binding != request_binding:
        return False
    return True


APPROVAL_BINDING_FIELDS: tuple[str, ...] = (
    "effect_set", "normalized_resources", "argument_digest", "credential_exposure",
    "reversibility", "run_id", "tool_call_identity", "tool_schema_digest",
)


def requires_new_approval(previous_binding: dict[str, Any], proposed_binding: dict[str, Any]) -> bool:
    """9.12.6/INV-APPROVAL-002: any material difference in a binding field requires a new approval."""
    for field in APPROVAL_BINDING_FIELDS:
        prev = previous_binding.get(field)
        new = proposed_binding.get(field)
        if field == "effect_set":
            if set(prev or []) != set(new or []):
                return True
        elif field == "normalized_resources":
            if _resource_list_key(prev) != _resource_list_key(new):
                return True
        elif prev != new:
            return True
    return False


def _resource_list_key(resources: Any) -> tuple[tuple[str, str], ...]:
    if not resources:
        return ()
    return tuple(sorted((r.get("kind"), r.get("normalized_key")) for r in resources))
