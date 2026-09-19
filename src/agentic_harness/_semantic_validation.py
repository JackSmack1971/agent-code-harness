"""Cross-field invariants for `SemanticTypes v1` (Blueprint 10.3) that plain
JSON Schema cannot express (arithmetic relationships between two fields).

Structural shape is owned by `contracts/semantic_types.schema.json`; this
module owns only the invariants that schema's $comment blocks defer here.
"""

from __future__ import annotations

REASON_CODE_INVALID_CONTRACT_VALUE = "CONFIG_INVALID_CONTRACT_VALUE"

__all__ = ["EvidenceRequirementError", "validate_evidence_requirement", "REASON_CODE_INVALID_CONTRACT_VALUE"]


class EvidenceRequirementError(ValueError):
    def __init__(self, message: str, *, reason_code: str = REASON_CODE_INVALID_CONTRACT_VALUE) -> None:
        super().__init__(message)
        self.reason_code = reason_code


def validate_evidence_requirement(mode: str, claim_refs: list[str], threshold: int | None) -> None:
    """Enforce 10.3.4: THRESHOLD requires `1 <= threshold <= len(claim_refs)`;
    ALL and ANY require `threshold` to be null.
    """
    if not claim_refs:
        raise EvidenceRequirementError("EvidenceRequirement.claim_refs must be a non-empty ordered list")

    if mode == "THRESHOLD":
        if threshold is None:
            raise EvidenceRequirementError("THRESHOLD mode requires a non-null threshold")
        if not (1 <= threshold <= len(claim_refs)):
            raise EvidenceRequirementError(
                f"threshold {threshold} is out of range for {len(claim_refs)} claim_refs "
                "(must satisfy 1 <= threshold <= len(claim_refs))"
            )
    elif mode in ("ALL", "ANY"):
        if threshold is not None:
            raise EvidenceRequirementError(f"{mode} mode requires threshold to be null, got {threshold!r}")
    else:
        raise EvidenceRequirementError(f"unknown EvidenceRequirement.mode {mode!r}")
