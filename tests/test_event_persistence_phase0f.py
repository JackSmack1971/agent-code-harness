from __future__ import annotations

import hashlib
import sqlite3
import subprocess
import sys
from dataclasses import replace

import pytest

from agentic_harness._classification import SecretRegistration
from agentic_harness._events import EventRegistryError, make_event, registered_events, validate_payload
from agentic_harness._persistence import PersistenceError, SQLiteStore
from agentic_harness._side_effects import (
    ContentAddressedStore,
    RecoveryClassification,
    SideEffectFamily,
    SideEffectError,
    TxnPhase,
    classify_recovery,
    prepare_txn,
    reconcile_txn,
    record_observation,
    retry_allowed,
)


def test_registry_is_complete_and_strict():
    registry = registered_events()
    assert len(registry) >= 40
    assert {"run.created", "approval.consumed", "reconciliation.completed"} <= registry.keys()
    for entry in registry.values():
        assert entry["payload_schema"]["additionalProperties"] is False
        assert entry["payload_schema"]["properties"]
    with pytest.raises(EventRegistryError):
        validate_payload("run.created", {"run_id": "r", "secret": "must reject"})
    with pytest.raises(EventRegistryError):
        validate_payload("not.registered", {})


def test_first_event_causality_and_sequence():
    event = make_event(run_id="run-1", sequence=1, event_type="run.created", payload={"run_id": "run-1"}, actor_type="RUNTIME")
    assert event.causation_event_id is None
    assert event.correlation_id == "run-1"
    with pytest.raises(EventRegistryError):
        make_event(run_id="run-1", sequence=1, event_type="run.created", payload={"run_id": "run-1"}, actor_type="RUNTIME", causation_event_id="e")
    redacted = make_event(run_id="run-1", sequence=2, event_type="run.blocked", payload={"reason": "token=plain"}, actor_type="RUNTIME", causation_event_id=event.event_id, secret_registrations=[SecretRegistration("s", "plain")])
    assert redacted.payload["reason"] == "token=<REDACTED:s>"
    assert redacted.redaction_applied


def test_domain_and_event_are_one_transaction(tmp_path):
    store = SQLiteStore(tmp_path / "state.db")
    store.conn.execute("INSERT INTO runs(run_id,state,run_version,created_at,updated_at) VALUES('r','NEW',0,'t','t')")
    event = make_event(run_id="r", sequence=1, event_type="run.created", payload={"run_id": "r"}, actor_type="RUNTIME")
    store.mutate_with_event(lambda c: c.execute("UPDATE runs SET run_version=1 WHERE run_id='r'"), event)
    assert store.conn.execute("SELECT run_version FROM runs WHERE run_id='r'").fetchone()[0] == 1
    assert store.conn.execute("SELECT sequence FROM events WHERE run_id='r'").fetchone()[0] == 1
    bad = make_event(run_id="r", sequence=3, event_type="run.blocked", payload={"reason": "x"}, actor_type="RUNTIME")
    with pytest.raises(PersistenceError):
        store.mutate_with_event(lambda c: c.execute("UPDATE runs SET state='BLOCKED' WHERE run_id='r'"), bad)
    assert store.conn.execute("SELECT state FROM runs WHERE run_id='r'").fetchone()[0] == "NEW"
    duplicate_id = make_event(run_id="r", sequence=2, event_type="run.blocked", payload={"reason": "x"}, actor_type="RUNTIME")
    # Reuse the committed first event ID to force the event insert to fail.
    duplicate_id = replace(duplicate_id, event_id=event.event_id)
    with pytest.raises(sqlite3.IntegrityError):
        store.mutate_with_event(lambda c: c.execute("UPDATE runs SET state='FAILED' WHERE run_id='r'"), duplicate_id)
    assert store.conn.execute("SELECT state FROM runs WHERE run_id='r'").fetchone()[0] == "NEW"


def test_side_effect_recovery_is_not_blind_retry():
    assert classify_recovery(effect_observed=False, post_digest=None, requested_post_digest="sha256:x") == RecoveryClassification.NOT_APPLIED
    assert classify_recovery(effect_observed=True, post_digest="sha256:x", requested_post_digest="sha256:x") == RecoveryClassification.APPLIED_MATCH
    assert classify_recovery(effect_observed=True, post_digest="sha256:y", requested_post_digest="sha256:x") == RecoveryClassification.APPLIED_DIVERGENT
    assert classify_recovery(effect_observed=None, post_digest=None, requested_post_digest="sha256:x") == RecoveryClassification.UNKNOWN
    assert retry_allowed(RecoveryClassification.NOT_APPLIED)
    assert not retry_allowed(RecoveryClassification.UNKNOWN)
    assert not retry_allowed(RecoveryClassification.APPLIED_DIVERGENT)


def test_side_effect_journal_and_cas_corruption(tmp_path):
    store = SQLiteStore(tmp_path / "state.db")
    store.conn.execute("INSERT INTO runs(run_id,state,run_version,created_at,updated_at) VALUES('r','NEW',0,'t','t')")
    txn = prepare_txn(store.conn, run_id="r", tool_call_id="tool", family=SideEffectFamily.FILESYSTEM, request={"path": "a"})
    assert store.conn.execute("SELECT phase FROM side_effect_txns WHERE txn_id=?", (txn.txn_id,)).fetchone()[0] == "PREPARED"
    record_observation(store.conn, txn.txn_id, TxnPhase.APPLYING)
    record_observation(store.conn, txn.txn_id, TxnPhase.RECONCILIATION_REQUIRED, "sha256:drift")
    assert store.conn.execute("SELECT phase FROM side_effect_txns WHERE txn_id=?", (txn.txn_id,)).fetchone()[0] == "RECONCILIATION_REQUIRED"
    cas = ContentAddressedStore(tmp_path / "objects")
    digest, rel = cas.put(b"one")
    path = tmp_path / "objects" / rel
    path.write_bytes(b"two")
    with pytest.raises(SideEffectError, match="PERSIST_CORRUPT"):
        cas.put(b"one")
    assert not cas.verify(digest)

    orphan = ContentAddressedStore(tmp_path / "orphan-objects")
    orphan_digest = "sha256:" + hashlib.sha256(b"orphan").hexdigest()
    orphan_rel = tmp_path / "orphan-objects" / "objects" / "sha256" / orphan_digest[7:9] / orphan_digest[9:11] / orphan_digest[11:]
    orphan_rel.parent.mkdir(parents=True)
    orphan_rel.write_bytes(b"orphan")
    assert orphan.put(b"orphan")[0] == orphan_digest
    assert orphan.verify(orphan_digest)


def test_jsonl_is_a_committed_sqlite_projection(tmp_path):
    store = SQLiteStore(tmp_path / "state.db")
    store.conn.execute("INSERT INTO runs(run_id,state,run_version,created_at,updated_at) VALUES('r','NEW',0,'t','t')")
    first = make_event(run_id="r", sequence=1, event_type="run.created", payload={"run_id": "r"}, actor_type="RUNTIME")
    store.mutate_with_event(lambda c: None, first)
    line = store.events_jsonl("r")
    assert line.endswith(b"\n") and line.count(b"\n") == 1
    assert line == first.canonical_bytes() + b"\n"


def test_reconciliation_persists_match_or_blocks_unknown(tmp_path):
    store = SQLiteStore(tmp_path / "state.db")
    store.conn.execute("INSERT INTO runs(run_id,state,run_version,created_at,updated_at) VALUES('r','NEW',0,'t','t')")
    matched = prepare_txn(store.conn, run_id="r", tool_call_id="m", family=SideEffectFamily.GIT, request={"ref": "x"})
    assert reconcile_txn(store.conn, matched.txn_id, effect_observed=True, post_state_digest="sha256:x", requested_post_digest="sha256:x") == RecoveryClassification.APPLIED_MATCH
    assert store.conn.execute("SELECT phase FROM side_effect_txns WHERE txn_id=?", (matched.txn_id,)).fetchone()[0] == TxnPhase.OBSERVED_APPLIED.value
    unknown = prepare_txn(store.conn, run_id="r", tool_call_id="u", family=SideEffectFamily.EXTERNAL_WRITE, request={"url": "x"})
    assert reconcile_txn(store.conn, unknown.txn_id, effect_observed=None, post_state_digest=None, requested_post_digest="sha256:x") == RecoveryClassification.UNKNOWN
    assert store.conn.execute("SELECT phase FROM side_effect_txns WHERE txn_id=?", (unknown.txn_id,)).fetchone()[0] == TxnPhase.RECONCILIATION_REQUIRED.value


def test_process_kill_leaves_durable_prepared_intent(tmp_path):
    db = tmp_path / "killed.db"
    script = """
from agentic_harness._persistence import SQLiteStore
from agentic_harness._side_effects import SideEffectFamily, prepare_txn
import os, sys
s=SQLiteStore(sys.argv[1])
s.conn.execute(\"INSERT INTO runs(run_id,state,run_version,created_at,updated_at) VALUES('r','NEW',0,'t','t')\")
prepare_txn(s.conn, run_id='r', tool_call_id='t', family=SideEffectFamily.PROCESS, request={'argv':['x']})
os._exit(9)
"""
    result = subprocess.run([sys.executable, "-c", script, str(db)], check=False)
    assert result.returncode == 9
    store = SQLiteStore(db)
    assert store.conn.execute("SELECT phase FROM side_effect_txns").fetchone()[0] == TxnPhase.PREPARED.value


def test_newer_schema_and_bad_migration_checksum_fail_closed(tmp_path):
    newer = tmp_path / "newer.db"
    conn = sqlite3.connect(newer)
    conn.execute("CREATE TABLE schema_meta(schema_version INTEGER PRIMARY KEY, applied_at TEXT, migration_digest TEXT)")
    conn.execute("INSERT INTO schema_meta VALUES(99,'t','sha256:future')")
    conn.commit()
    conn.close()
    with pytest.raises(PersistenceError, match="newer"):
        SQLiteStore(newer)

    bad = tmp_path / "bad.db"
    store = SQLiteStore(bad)
    store.conn.execute("UPDATE schema_migrations SET source_digest='sha256:tampered'")
    store.close()
    with pytest.raises(PersistenceError, match="checksum"):
        SQLiteStore(bad)


def test_approval_consumption_is_atomic_with_prepared_intent(tmp_path):
    store = SQLiteStore(tmp_path / "state.db")
    store.conn.execute("INSERT INTO runs(run_id,state,run_version,created_at,updated_at) VALUES('r','NEW',0,'t','t')")
    store.conn.execute("INSERT INTO approval_requests(approval_id,run_id,request_digest,disposition,canonical_json,created_at) VALUES('a','r','sha256:r','GRANTED','{}','t')")
    txn = prepare_txn(store.conn, run_id="r", tool_call_id="tool", family=SideEffectFamily.PROCESS, request={"argv": ["x"]}, approval_id="a")
    assert store.conn.execute("SELECT consumed_count FROM approval_requests WHERE approval_id='a'").fetchone()[0] == 1
    assert store.conn.execute("SELECT txn_id FROM approval_consumptions WHERE approval_id='a'").fetchone()[0] == txn.txn_id
    with pytest.raises(SideEffectError):
        prepare_txn(store.conn, run_id="r", tool_call_id="tool2", family=SideEffectFamily.PROCESS, request={"argv": ["y"]}, approval_id="a")
    assert store.conn.execute("SELECT count(*) FROM side_effect_txns").fetchone()[0] == 1


@pytest.mark.parametrize("family", list(SideEffectFamily))
def test_every_effect_family_has_a_durable_intent(tmp_path, family):
    store = SQLiteStore(tmp_path / f"{family.value}.db")
    store.conn.execute("INSERT INTO runs(run_id,state,run_version,created_at,updated_at) VALUES('r','NEW',0,'t','t')")
    txn = prepare_txn(store.conn, run_id="r", tool_call_id=family.value, family=family, request={"family": family.value})
    row = store.conn.execute("SELECT family,phase FROM side_effect_txns WHERE txn_id=?", (txn.txn_id,)).fetchone()
    assert (row[0], row[1]) == (family.value, TxnPhase.PREPARED.value)
