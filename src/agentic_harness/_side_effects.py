"""Durable side-effect intent and family-neutral reconciliation primitives."""
from __future__ import annotations

import hashlib
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Callable

from ._canonical import digest_for
from ._identity import uuid7_str


class SideEffectError(RuntimeError):
    pass


class SideEffectFamily(StrEnum):
    FILESYSTEM = "FILESYSTEM"
    GIT = "GIT"
    PROCESS = "PROCESS"
    EXTERNAL_WRITE = "EXTERNAL_WRITE"
    APPROVAL_CONSUMPTION = "APPROVAL_CONSUMPTION"
    ARTIFACT_WRITE = "ARTIFACT_WRITE"
    INTEGRATION = "INTEGRATION"


class TxnPhase(StrEnum):
    PREPARED = "PREPARED"
    APPLYING = "APPLYING"
    OBSERVED_APPLIED = "OBSERVED_APPLIED"
    COMMITTED = "COMMITTED"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    ABORTED = "ABORTED"


class RecoveryClassification(StrEnum):
    NOT_APPLIED = "NOT_APPLIED"
    APPLIED_MATCH = "APPLIED_MATCH"
    APPLIED_DIVERGENT = "APPLIED_DIVERGENT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class SideEffectTxn:
    txn_id: str
    run_id: str
    tool_call_id: str
    family: SideEffectFamily
    request_digest: str
    pre_state_digest: str | None = None
    phase: TxnPhase = TxnPhase.PREPARED
    post_state_digest: str | None = None


def classify_recovery(*, effect_observed: bool | None, post_digest: str | None, requested_post_digest: str | None) -> RecoveryClassification:
    if effect_observed is False:
        return RecoveryClassification.NOT_APPLIED
    if effect_observed is None:
        return RecoveryClassification.UNKNOWN
    if requested_post_digest is not None and post_digest == requested_post_digest:
        return RecoveryClassification.APPLIED_MATCH
    return RecoveryClassification.APPLIED_DIVERGENT


def retry_allowed(classification: RecoveryClassification) -> bool:
    """Only a proven absent effect may be executed; uncertainty is fail-closed."""
    return classification is RecoveryClassification.NOT_APPLIED


_ALLOWED_PHASE_TRANSITIONS: dict[TxnPhase, frozenset[TxnPhase]] = {
    TxnPhase.PREPARED: frozenset({TxnPhase.APPLYING, TxnPhase.OBSERVED_APPLIED, TxnPhase.RECONCILIATION_REQUIRED, TxnPhase.ABORTED}),
    TxnPhase.APPLYING: frozenset({TxnPhase.OBSERVED_APPLIED, TxnPhase.RECONCILIATION_REQUIRED, TxnPhase.ABORTED}),
    TxnPhase.OBSERVED_APPLIED: frozenset({TxnPhase.COMMITTED, TxnPhase.RECONCILIATION_REQUIRED}),
    TxnPhase.COMMITTED: frozenset(),
    TxnPhase.RECONCILIATION_REQUIRED: frozenset({TxnPhase.COMMITTED, TxnPhase.ABORTED}),
    TxnPhase.ABORTED: frozenset(),
}


def prepare_txn(conn: sqlite3.Connection, *, run_id: str, tool_call_id: str, family: SideEffectFamily,
                request: object, pre_state_digest: str | None = None, txn_id: str | None = None,
                approval_id: str | None = None) -> SideEffectTxn:
    txn = SideEffectTxn(txn_id or uuid7_str(), run_id, tool_call_id, family, digest_for(request), pre_state_digest)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("INSERT INTO side_effect_txns(txn_id,run_id,tool_call_id,family,request_digest,pre_state_digest,phase,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                     (txn.txn_id, txn.run_id, txn.tool_call_id, txn.family.value, txn.request_digest, txn.pre_state_digest, txn.phase.value, now, now))
        if approval_id is not None:
            row = conn.execute("SELECT revoked_at, consumed_count FROM approval_requests WHERE approval_id=? AND run_id=?", (approval_id, run_id)).fetchone()
            if row is None or row[0] is not None or row[1] > 0:
                raise SideEffectError("approval is unavailable")
            conn.execute("UPDATE approval_requests SET consumed_count=consumed_count+1 WHERE approval_id=?", (approval_id,))
            conn.execute("INSERT INTO approval_consumptions(approval_id,txn_id,consumed_at) VALUES(?,?,?)", (approval_id, txn.txn_id, now))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return txn


def record_observation(conn: sqlite3.Connection, txn_id: str, phase: TxnPhase, post_state_digest: str | None = None) -> None:
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute("SELECT phase FROM side_effect_txns WHERE txn_id=?", (txn_id,)).fetchone()
        if row is None:
            raise SideEffectError("unknown side-effect transaction")
        current = TxnPhase(row[0])
        if phase not in _ALLOWED_PHASE_TRANSITIONS[current]:
            raise SideEffectError(f"invalid side-effect transition {current.value}->{phase.value}")
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        conn.execute("UPDATE side_effect_txns SET phase=?,post_state_digest=?,updated_at=? WHERE txn_id=?", (phase.value, post_state_digest, now, txn_id))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def reconcile_txn(conn: sqlite3.Connection, txn_id: str, *, effect_observed: bool | None,
                  post_state_digest: str | None, requested_post_digest: str | None) -> RecoveryClassification:
    """Classify an interrupted intent and persist only a safe recovery phase.

    NOT_APPLIED stays PREPARED and may be executed once. Every other uncertain
    or divergent result is durable reconciliation work and cannot be retried as
    a fresh effect.
    """
    classification = classify_recovery(effect_observed=effect_observed, post_digest=post_state_digest,
                                       requested_post_digest=requested_post_digest)
    if classification is RecoveryClassification.NOT_APPLIED:
        return classification
    target = (TxnPhase.OBSERVED_APPLIED if classification is RecoveryClassification.APPLIED_MATCH
              else TxnPhase.RECONCILIATION_REQUIRED)
    record_observation(conn, txn_id, target, post_state_digest)
    return classification


class ContentAddressedStore:
    def __init__(self, root: str | os.PathLike[str]):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, data: bytes) -> tuple[str, str]:
        digest = "sha256:" + hashlib.sha256(data).hexdigest()
        rel = Path("objects") / "sha256" / digest[7:9] / digest[9:11] / digest[11:]
        target = self.root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if target.read_bytes() != data:
                raise SideEffectError("PERSIST_CORRUPT: digest path contains different bytes")
            return digest, str(rel)
        temp = target.with_name(target.name + ".tmp-" + uuid7_str())
        try:
            with temp.open("wb") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(temp, target)
            try:
                dir_fd = os.open(target.parent, os.O_RDONLY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            except OSError:
                # Directory fsync is unavailable on some supported platforms;
                # the file fsync plus atomic replace remain mandatory.
                pass
            if target.read_bytes() != data:
                raise SideEffectError("PERSIST_CORRUPT: installed object failed verification")
        finally:
            temp.unlink(missing_ok=True)
        return digest, str(rel)

    def verify(self, digest: str) -> bool:
        if not digest.startswith("sha256:") or len(digest) != 71:
            raise SideEffectError("invalid artifact digest")
        rel = Path("objects") / "sha256" / digest[7:9] / digest[9:11] / digest[11:]
        target = self.root / rel
        if not target.is_file():
            return False
        return "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest() == digest
