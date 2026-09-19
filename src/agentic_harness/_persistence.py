"""SQLite authority for PersistenceSchema v1."""
from __future__ import annotations

import os
import sqlite3
from typing import Any, Callable

from ._canonical import canonical_json_bytes, digest_for
from ._contracts import find_contracts_root
from ._events import EventEnvelope


SCHEMA_VERSION = 1
MIGRATION_DIGEST = "sha256:phase0f-schema-v1"
class PersistenceError(RuntimeError):
    pass


class SQLiteStore:
    def __init__(self, path: str | os.PathLike[str]):
        self.path = str(path)
        self.conn = sqlite3.connect(self.path, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self._migrate()

    def _migrate(self) -> None:
        try:
            # executescript() manages its own SQLite transaction boundary.  Do
            # not wrap it in a Python transaction: sqlite3 commits an active
            # transaction before executing a script, which would make failure
            # handling falsely report a successful/rollback-able migration.
            contracts_root = find_contracts_root()
            if contracts_root is None:
                raise PersistenceError("authoritative persistence.sql is unavailable")
            schema_path = contracts_root / "persistence.sql"
            known = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_meta'").fetchone()
            if known:
                current = self.conn.execute("SELECT COALESCE(MAX(schema_version), 0) FROM schema_meta").fetchone()[0]
                if current > SCHEMA_VERSION:
                    raise PersistenceError(f"database schema {current} is newer than runtime {SCHEMA_VERSION}")
            self.conn.executescript(schema_path.read_text(encoding="utf-8"))
            current = self.conn.execute("SELECT COALESCE(MAX(schema_version), 0) FROM schema_meta").fetchone()[0]
            if current > SCHEMA_VERSION:
                raise PersistenceError(f"database schema {current} is newer than runtime {SCHEMA_VERSION}")
            bad = self.conn.execute("SELECT migration_id FROM schema_migrations WHERE schema_version=? AND source_digest<>?", (SCHEMA_VERSION, MIGRATION_DIGEST)).fetchone()
            if bad:
                raise PersistenceError(f"migration checksum mismatch: {bad[0]}")
        except Exception:
            raise

    def close(self) -> None:
        self.conn.close()

    def mutate_with_event(self, mutation: Callable[[sqlite3.Connection], Any], event: EventEnvelope) -> Any:
        """Commit a domain mutation and its event atomically, with strict per-run sequencing."""
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            result = mutation(self.conn)
            last = self.conn.execute("SELECT COALESCE(MAX(sequence), 0) FROM events WHERE run_id=?", (event.run_id,)).fetchone()[0]
            if event.sequence != last + 1:
                raise PersistenceError(f"expected event sequence {last + 1}, got {event.sequence}")
            if event.sequence == 1 and event.causation_event_id is not None:
                raise PersistenceError("first event cannot have a causation event")
            if event.causation_event_id is not None:
                parent = self.conn.execute("SELECT run_id FROM events WHERE event_id=?", (event.causation_event_id,)).fetchone()
                if parent is None or parent[0] != event.run_id:
                    raise PersistenceError("causation event must exist in the same run")
            self.conn.execute(
                "INSERT INTO events(event_id,run_id,sequence,event_type,event_version,occurred_at,canonical_json,payload_digest) VALUES(?,?,?,?,?,?,?,?)",
                (event.event_id, event.run_id, event.sequence, event.event_type, event.event_version,
                 event.occurred_at, canonical_json_bytes(event.as_dict()).decode(), event.payload_digest),
            )
            self.conn.execute("COMMIT")
            return result
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def events_jsonl(self, run_id: str) -> bytes:
        rows = self.conn.execute("SELECT canonical_json FROM events WHERE run_id=? ORDER BY sequence", (run_id,)).fetchall()
        return b"".join(row[0].encode() + b"\n" for row in rows)

    def consume_approval(self, approval_id: str, txn_id: str) -> None:
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute("SELECT revoked_at, consumed_count FROM approval_requests WHERE approval_id=?", (approval_id,)).fetchone()
            if row is None or row[0] is not None or row[1] > 0:
                raise PersistenceError("approval is unavailable")
            self.conn.execute("UPDATE approval_requests SET consumed_count=consumed_count+1 WHERE approval_id=?", (approval_id,))
            self.conn.execute("INSERT INTO approval_consumptions(approval_id,txn_id,consumed_at) VALUES(?,?,datetime('now'))", (approval_id, txn_id))
            self.conn.execute("COMMIT")
        except Exception:
            self.conn.execute("ROLLBACK")
            raise
