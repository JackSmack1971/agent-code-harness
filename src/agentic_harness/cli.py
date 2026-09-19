"""Headless-safe `harness` CLI and CLIProtocol v1 result envelopes."""

from __future__ import annotations

import json
import datetime as dt
import os
import platform
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

import typer
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from agentic_harness import __version__
from agentic_harness._canonical import canonical_json_bytes
from agentic_harness._config import ConfigError, compute_config_digest, resolve_configuration_from_files
from agentic_harness._contracts import find_contracts_root, find_research_record, load_contract_set, load_json
from agentic_harness._domain_schemas import compute_identity_digest, validate_record
from agentic_harness._events import make_event
from agentic_harness._identity import uuid7_str
from agentic_harness._persistence import SQLiteStore
from agentic_harness._reason_codes import CommandStatus, ExitClass

app = typer.Typer(name="harness", help="Agentic Coding Harness CLI.", no_args_is_help=True, add_completion=False)
config_app = typer.Typer(name="config", help="Configuration commands.", no_args_is_help=True)
contracts_app = typer.Typer(name="contracts", help="Contract commands.", no_args_is_help=True)
app.add_typer(config_app, name="config")
app.add_typer(contracts_app, name="contracts")

_EXIT_BY_STATUS = {
    CommandStatus.SUCCESS: ExitClass.SUCCESS,
    CommandStatus.INVALID: ExitClass.INVALID_USAGE_OR_CONFIG,
    CommandStatus.APPROVAL_REQUIRED: ExitClass.APPROVAL_UNAVAILABLE,
    CommandStatus.POLICY_DENIED: ExitClass.POLICY_DENIED,
    CommandStatus.VERIFICATION_FAILED: ExitClass.VERIFICATION_FAILED,
    CommandStatus.INCONCLUSIVE: ExitClass.UNVERIFIABLE_INCONCLUSIVE,
    CommandStatus.CORRUPT: ExitClass.PERSISTENCE_CORRUPTION,
    CommandStatus.INTEGRATION_CONFLICT: ExitClass.INTEGRATION_CONFLICT,
    CommandStatus.INTERRUPTED: ExitClass.INTERRUPTED,
    CommandStatus.UNSUPPORTED: ExitClass.UNSUPPORTED_CAPABILITY,
    CommandStatus.EXTERNAL_FAILURE: ExitClass.EXTERNAL_FAILURE,
    CommandStatus.INTERNAL_FAILURE: ExitClass.INTERNAL_FAILURE,
}


def _envelope(command: str, status: str, code: str, message: str, *, run_id: str | None = None, state: str | None = None, data: Any = None) -> dict[str, Any]:
    return {"protocol": "harness.cli", "protocol_version": 1, "command": command, "status": status, "symbolic_code": code, "run_id": run_id, "state": state, "message": message, "data": data}


def _emit(envelope: dict[str, Any], json_output: bool) -> None:
    _validate_envelope(envelope)
    if json_output:
        typer.echo(json.dumps(envelope, separators=(",", ":"), sort_keys=True, ensure_ascii=False))
        return
    typer.echo(f"{envelope['command']}: {envelope['status']} ({envelope['symbolic_code']})")
    typer.echo(envelope["message"])


def _validate_envelope(envelope: dict[str, Any]) -> None:
    root = find_contracts_root()
    if root is None:
        return
    Draft202012Validator(load_json(root / "cli_protocol.schema.json")).validate(envelope)
    if not isinstance(envelope.get("data"), dict):
        return
    command_file = {"doctor": "doctor", "run": "run", "status": "status", "resume": "resume", "accept": "accept", "reject": "reject", "cancel": "cancel", "inspect": "inspect", "config validate": "config_validate", "contracts check": "contracts_check"}.get(envelope["command"])
    if command_file:
        path = root / "cli_protocol" / "data" / f"{command_file}.schema.json"
        if path.is_file():
            Draft202012Validator(load_json(path)).validate(envelope["data"])


def _finish(envelope: dict[str, Any], json_output: bool) -> None:
    _emit(envelope, json_output)
    raise typer.Exit(code=int(_EXIT_BY_STATUS[envelope["status"]]))


def _check_python(manifest: dict[str, Any]) -> dict[str, Any]:
    from agentic_harness._versioning import at_least, below
    cfg = manifest["python"]
    actual = platform.python_version()
    supported = at_least(actual, cfg["min_inclusive"]) and below(actual, cfg["max_exclusive"])
    return {"capability": "PYTHON_RUNTIME", "status": "SUPPORTED" if supported else "UNSUPPORTED", "observed_version": actual, "required_specifier": cfg["specifier"]}


def _check_git(register: list[dict[str, Any]]) -> dict[str, Any]:
    from agentic_harness._versioning import at_least
    record = find_research_record(register, "GIT_MIN_VERSION")
    git_path = shutil.which("git")
    if git_path is None:
        return {"capability": "GIT_MIN_VERSION", "status": "BLOCKED_CAPABILITY", "reason": "system git executable not found on PATH"}
    proc = subprocess.run([git_path, "--version"], capture_output=True, text=True, check=False, timeout=10)
    observed = proc.stdout.strip() if proc.returncode == 0 else None
    if not observed or not record or record.get("resolved_value") is None:
        return {"capability": "GIT_MIN_VERSION", "status": "BLOCKED_CAPABILITY", "observed_version": observed, "reason": "research record unresolved or git invocation failed"}
    minimum = record["resolved_value"]
    return {"capability": "GIT_MIN_VERSION", "status": "SUPPORTED" if at_least(observed, minimum) else "UNSUPPORTED", "observed_version": observed, "required_minimum": minimum, "source_refs": record.get("source_refs", [])}


@app.command()
def version() -> None:
    typer.echo(__version__)
    raise typer.Exit(code=0)


@app.command()
def doctor(json_output: bool = typer.Option(False, "--json")) -> None:
    contracts = load_contract_set()
    if contracts is None:
        _finish(_envelope("doctor", CommandStatus.UNSUPPORTED, "CLI_UNSUPPORTED_CAPABILITY", "Could not locate canonical contracts/"), json_output)
    checks = [_check_python(contracts.product_manifest), _check_git(contracts.research_register), {"capability": "GIT_SHA256_REPOSITORY_SUPPORT", "status": "BLOCKED_CAPABILITY", "reason": "dual object-format support is not proven"}]
    _finish(_envelope("doctor", CommandStatus.SUCCESS, "CLI_DOCTOR_REPORT", "Capability report generated.", data={"checks": checks, "contracts_root": str(contracts.root)}), json_output)


def _db_path(repo: Path) -> Path:
    return repo / ".harness" / "state.sqlite3"


def _open_db(repo: Path, *, create: bool = False) -> SQLiteStore:
    path = _db_path(repo)
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
    return SQLiteStore(path)


def _new_goal(objective: str, now: str) -> dict[str, Any]:
    goal = {
        "schema_name": "GoalContract", "schema_version": 1,
        "goal_id": uuid7_str(), "goal_revision_id": uuid7_str(), "parent_revision_id": None,
        "intent": objective, "desired_outcome": objective, "constraints": [],
        "acceptance_criteria": [], "uncertainties": [], "created_at": now, "source": "USER",
        "digest": "sha256:" + "0" * 64,
    }
    goal["digest"] = compute_identity_digest("GoalContract", goal)
    return goal


@app.command()
def run(objective: str | None = typer.Argument(None), objective_file: Path | None = typer.Option(None, "--objective-file"), repo: Path = typer.Option(Path.cwd(), "--repo"), config: Path | None = typer.Option(None, "--config"), json_output: bool = typer.Option(False, "--json")) -> None:
    if (objective is None) == (objective_file is None):
        _finish(_envelope("run", CommandStatus.INVALID, "CLI_INVALID_USAGE", "Provide exactly one objective or --objective-file."), json_output)
    try:
        text_value = objective if objective is not None else objective_file.read_text(encoding="utf-8")
        if not text_value.strip():
            raise ValueError("objective must not be empty")
        config_digest = None
        if config is not None:
            root = find_contracts_root()
            if root is None:
                raise ConfigError("contracts root not found")
            effective = resolve_configuration_from_files(platform=sys.platform, repository_root=repo.resolve(), env=dict(os.environ), explicit_path=config, contracts_root=root)
            config_digest = compute_config_digest(effective)
        run_id = uuid7_str()
        now = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
        goal = _new_goal(text_value, now)
        validate_record("GoalContract", goal)
        run_record = {"schema_name": "RunRecord", "schema_version": 1, "run_id": run_id, "state": "CREATED", "run_version": 0,
            "goal_revision_id": goal["goal_revision_id"], "change_revision_id": None, "repository_snapshot_digest": None,
            "candidate_snapshot_digest": None, "config_digest": config_digest, "policy_digest": None, "resume_target_state": None,
            "created_at": now, "updated_at": now, "digest": "sha256:" + "0" * 64}
        run_record["digest"] = compute_identity_digest("RunRecord", run_record)
        store = _open_db(repo.resolve(), create=True); conn = store.conn
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("INSERT INTO goals(goal_id,created_at) VALUES(?,?)", (goal["goal_id"], now))
        conn.execute("INSERT INTO goal_revisions(goal_revision_id,goal_id,parent_revision_id,canonical_json,digest,created_at) VALUES(?,?,?,?,?,?)", (goal["goal_revision_id"], goal["goal_id"], None, canonical_json_bytes(goal).decode(), goal["digest"], now))
        conn.execute("INSERT INTO runs(run_id,state,run_version,goal_revision_id,change_revision_id,repository_snapshot_digest,candidate_snapshot_digest,config_digest,policy_digest,resume_target_state,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (run_id, "CREATED", 0, goal["goal_revision_id"], None, None, None, config_digest, None, None, now, now))
        conn.commit(); store.close()
        _finish(_envelope("run", CommandStatus.SUCCESS, "CLI_RUN_CREATED", "Run created; execution is ready for the deterministic runtime.", run_id=run_id, state="CREATED", data={"run_id": run_id, "state": "CREATED", "goal_revision_id": goal["goal_revision_id"], "blocker": None}), json_output)
    except (OSError, ValueError, sqlite3.Error) as exc:
        _finish(_envelope("run", CommandStatus.INVALID, "CLI_INVALID_USAGE", str(exc)), json_output)


def _get_run(repo: Path, run_id: str) -> tuple[SQLiteStore, sqlite3.Row | None]:
    store = _open_db(repo)
    return store, store.conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()


def _interrupt(store: SQLiteStore, run_id: str, reason: str) -> None:
    row = store.conn.execute("SELECT COALESCE(MAX(sequence), 0) FROM events WHERE run_id=?", (run_id,)).fetchone()
    sequence = int(row[0]) + 1
    event = make_event(run_id=run_id, sequence=sequence, event_type="run.interrupted", payload={"reason": reason}, actor_type="SYSTEM")
    def mutation(conn: sqlite3.Connection) -> None:
        conn.execute("UPDATE runs SET state='INTERRUPTED', run_version=run_version+1, updated_at=? WHERE run_id=?", (dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"), run_id))
    store.mutate_with_event(mutation, event)


@app.command()
def status(run_id: str, repo: Path = typer.Option(Path.cwd(), "--repo"), json_output: bool = typer.Option(False, "--json")) -> None:
    conn, row = _get_run(repo.resolve(), run_id)
    if row is None:
        conn.close(); _finish(_envelope("status", CommandStatus.INVALID, "CLI_RUN_NOT_FOUND", "Run was not found.", run_id=run_id), json_output)
    conn.close()
    _finish(_envelope("status", CommandStatus.SUCCESS, "CLI_STATUS_OK", "Run status returned.", run_id=run_id, state=row["state"], data={"run_id": row["run_id"], "state": row["state"], "run_version": row["run_version"], "current_identities": {}, "pending_action": None}), json_output)


@app.command()
def resume(run_id: str, repo: Path = typer.Option(Path.cwd(), "--repo"), json_output: bool = typer.Option(False, "--json")) -> None:
    conn, row = _get_run(repo.resolve(), run_id)
    if row is None:
        conn.close(); _finish(_envelope("resume", CommandStatus.INVALID, "CLI_RUN_NOT_FOUND", "Run was not found.", run_id=run_id), json_output)
    state = row["state"]; conn.close()
    if state not in {"BLOCKED", "INTERRUPTED", "RECOVERY_REQUIRED", "RECONCILIATION_REQUIRED", "INTEGRATION_CONFLICT"}:
        _finish(_envelope("resume", CommandStatus.INVALID, "STATE_INVALID_TRANSITION", "Run is not resumable.", run_id=run_id, state=state, data={"resulting_state": state, "recovered_from": None, "blocker": "STATE_INVALID_TRANSITION"}), json_output)
    _finish(_envelope("resume", CommandStatus.INCONCLUSIVE, "RECOVERY_EXTERNAL_DRIFT", "Resume requires reconciled identities and durable evidence.", run_id=run_id, state=state, data={"resulting_state": state, "recovered_from": state, "blocker": "RECOVERY_EXTERNAL_DRIFT"}), json_output)


@app.command()
def reject(run_id: str, reason: str = typer.Option("", "--reason"), repo: Path = typer.Option(Path.cwd(), "--repo"), json_output: bool = typer.Option(False, "--json")) -> None:
    conn, row = _get_run(repo.resolve(), run_id)
    if row is None:
        conn.close(); _finish(_envelope("reject", CommandStatus.INVALID, "CLI_RUN_NOT_FOUND", "Run was not found.", run_id=run_id), json_output)
    if row["state"] == "REJECTED":
        code = "CLI_ALREADY_REJECTED"
    elif row["state"] in {"ACCEPTED", "FAILED"}:
        conn.close(); _finish(_envelope("reject", CommandStatus.INVALID, "STATE_INVALID_TRANSITION", "Terminal run cannot be rejected.", run_id=run_id, state=row["state"]), json_output)
    else:
        conn.conn.execute("BEGIN IMMEDIATE")
        conn.conn.execute("UPDATE runs SET state='REJECTED', run_version=run_version+1, updated_at=? WHERE run_id=?", (dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"), run_id))
        conn.conn.commit(); code = "CLI_REJECTED"
    conn.close(); _finish(_envelope("reject", CommandStatus.SUCCESS, code, "Run rejected.", run_id=run_id, state="REJECTED", data={"terminal_state": "REJECTED", "reason_artifact": None}), json_output)


@app.command()
def cancel(run_id: str, repo: Path = typer.Option(Path.cwd(), "--repo"), json_output: bool = typer.Option(False, "--json")) -> None:
    store, row = _get_run(repo.resolve(), run_id)
    if row is None:
        store.close(); _finish(_envelope("cancel", CommandStatus.INVALID, "CLI_RUN_NOT_FOUND", "Run was not found.", run_id=run_id), json_output)
    if row["state"] == "INTERRUPTED":
        store.close(); _finish(_envelope("cancel", CommandStatus.SUCCESS, "CLI_ALREADY_INTERRUPTED", "Run was already interrupted.", run_id=run_id, state="INTERRUPTED", data={"state": "INTERRUPTED", "checkpointed": True}), json_output)
    if row["state"] in {"ACCEPTED", "REJECTED", "FAILED"}:
        store.close(); _finish(_envelope("cancel", CommandStatus.INVALID, "STATE_INVALID_TRANSITION", "Terminal run cannot be interrupted.", run_id=run_id, state=row["state"]), json_output)
    try:
        _interrupt(store, run_id, "operator cancellation")
    except Exception as exc:
        store.close(); _finish(_envelope("cancel", CommandStatus.CORRUPT, "PERSIST_CORRUPT", str(exc), run_id=run_id), json_output)
    store.close(); _finish(_envelope("cancel", CommandStatus.INTERRUPTED, "TOOL_CANCELLED", "Run interrupted at a durable checkpoint.", run_id=run_id, state="INTERRUPTED", data={"state": "INTERRUPTED", "checkpointed": True}), json_output)


@app.command()
def accept(run_id: str, strategy: str = typer.Option("squash", "--strategy"), repo: Path = typer.Option(Path.cwd(), "--repo"), json_output: bool = typer.Option(False, "--json")) -> None:
    if strategy not in {"squash", "cherry-pick", "fast-forward", "patch-only"}:
        _finish(_envelope("accept", CommandStatus.INVALID, "CLI_INVALID_USAGE", "Unsupported integration strategy."), json_output)
    conn, row = _get_run(repo.resolve(), run_id)
    if row is None:
        conn.close(); _finish(_envelope("accept", CommandStatus.INVALID, "CLI_RUN_NOT_FOUND", "Run was not found.", run_id=run_id), json_output)
    if row["state"] == "ACCEPTED":
        integration = conn.conn.execute("SELECT destination_before,destination_after FROM integration_records WHERE run_id=? ORDER BY created_at DESC LIMIT 1", (run_id,)).fetchone()
        conn.close()
        if integration is None or integration[1] is None:
            _finish(_envelope("accept", CommandStatus.INTEGRATION_CONFLICT, "RECOVERY_EXTERNAL_DRIFT", "Landed destination identity is unavailable for an accepted run.", run_id=run_id, state="RECONCILIATION_REQUIRED", data={"strategy": strategy, "candidate_snapshot": row["candidate_snapshot_digest"], "destination_before": integration[0] if integration else None, "destination_after": None}), json_output)
        _finish(_envelope("accept", CommandStatus.SUCCESS, "CLI_ALREADY_ACCEPTED", "Run was already accepted with the recorded landed identity.", run_id=run_id, state="ACCEPTED", data={"strategy": strategy, "candidate_snapshot": row["candidate_snapshot_digest"], "destination_before": integration[0], "destination_after": integration[1]}), json_output)
    conn.close(); _finish(_envelope("accept", CommandStatus.INCONCLUSIVE, "VERIFY_INCONCLUSIVE", "ACCEPTED requires current READY_FOR_USER evidence, integration, and post-integration verification.", run_id=run_id, state=row["state"], data={"strategy": strategy, "candidate_snapshot": None, "destination_before": None, "destination_after": None}), json_output)


@app.command()
def inspect(run_id: str, artifact: str | None = typer.Option(None, "--artifact"), repo: Path = typer.Option(Path.cwd(), "--repo"), json_output: bool = typer.Option(False, "--json")) -> None:
    conn, row = _get_run(repo.resolve(), run_id)
    if row is None:
        conn.close(); _finish(_envelope("inspect", CommandStatus.INVALID, "CLI_RUN_NOT_FOUND", "Run was not found.", run_id=run_id), json_output)
    conn.close(); _finish(_envelope("inspect", CommandStatus.SUCCESS, "CLI_INSPECT_OK", "Typed inspection returned.", run_id=run_id, state=row["state"], data={"requested": "artifact" if artifact else "run", "artifact_id": artifact, "run": dict(row)}), json_output)


@config_app.command("validate")
def config_validate(path: Path | None = typer.Argument(None), json_output: bool = typer.Option(False, "--json")) -> None:
    try:
        root = find_contracts_root()
        if root is None: raise ConfigError("contracts root not found")
        effective = resolve_configuration_from_files(platform=sys.platform, repository_root=Path.cwd(), env=dict(os.environ), explicit_path=path, contracts_root=root)
        _finish(_envelope("config validate", CommandStatus.SUCCESS, "CLI_CONFIG_VALID", "Configuration is valid.", data={"config_digest": compute_config_digest(effective), "sources": [str(path)] if path else [], "warnings": []}), json_output)
    except Exception as exc:
        _finish(_envelope("config validate", CommandStatus.INVALID, getattr(exc, "reason_code", "CONFIG_INVALID"), str(exc)), json_output)


@contracts_app.command("check")
def contracts_check(json_output: bool = typer.Option(False, "--json")) -> None:
    root = find_contracts_root()
    if root is None:
        _finish(_envelope("contracts check", CommandStatus.UNSUPPORTED, "CLI_UNSUPPORTED_CAPABILITY", "Could not locate canonical contracts/"), json_output)
    files = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())
    failures: list[str] = []
    versions: dict[str, int] = {}
    schemas: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in sorted(root.rglob("*.schema.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(document)
            if "x-contract-name" in document:
                if document["x-contract-name"] in versions:
                    failures.append(f"duplicate contract name: {document['x-contract-name']}")
                versions[document["x-contract-name"]] = document.get("x-contract-version", 0)
            schema_id = document.get("$id")
            if not isinstance(schema_id, str):
                failures.append(f"{path.relative_to(root)}: missing $id")
            elif schema_id in schemas:
                failures.append(f"duplicate schema $id: {schema_id}")
            else:
                schemas[schema_id] = (path, document)
        except Exception as exc:
            failures.append(f"{path.relative_to(root)}: {exc}")
    schema_resources = []
    for path in sorted(root.rglob("*.schema.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
            if "$id" in document:
                schema_resources.append((document["$id"], Resource.from_contents(document)))
        except Exception:
            pass
    registry = Registry().with_resources(schema_resources)
    for path in sorted(root.rglob("*.yaml")):
        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
            schema_path = path.with_suffix(".schema.json")
            if schema_path.is_file() and isinstance(document, dict) and document.get("$schema") == json.loads(schema_path.read_text(encoding="utf-8")).get("$id"):
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                errors = sorted(Draft202012Validator(schema, registry=registry).iter_errors(document), key=str)
                if errors:
                    failures.append(f"{path.relative_to(root)}: {errors[0].message}")
        except Exception as exc:
            failures.append(f"{path.relative_to(root)}: {exc}")
    def walk_refs(value: Any) -> list[str]:
        refs: list[str] = []
        if isinstance(value, dict):
            if isinstance(value.get("$ref"), str):
                refs.append(value["$ref"])
            for child in value.values():
                refs.extend(walk_refs(child))
        elif isinstance(value, list):
            for child in value:
                refs.extend(walk_refs(child))
        return refs

    for schema_id, (path, document) in schemas.items():
        for reference in walk_refs(document):
            base, _, fragment = reference.partition("#")
            if base:
                if base.startswith("http"):
                    if base not in schemas:
                        failures.append(f"{path.relative_to(root)}: unresolved schema reference {reference}")
                elif not (path.parent / base).resolve().is_file():
                    failures.append(f"{path.relative_to(root)}: unresolved schema reference {reference}")
            if fragment and base.startswith("http") and base in schemas:
                node: Any = schemas[base][1]
                try:
                    for part in fragment.lstrip("/").split("/"):
                        node = node[part.replace("~1", "/").replace("~0", "~")]
                except (KeyError, TypeError):
                    failures.append(f"{path.relative_to(root)}: unresolved schema fragment {reference}")

    def load_yaml_file(relative: str) -> Any:
        return yaml.safe_load((root / relative).read_text(encoding="utf-8"))

    event_registry = load_yaml_file("event_registry.yaml")
    event_types = [entry.get("event_type") for entry in event_registry.get("events", [])]
    if len(event_types) != len(set(event_types)) or not event_types:
        failures.append("EventRegistry is not unique and non-empty")
    for entry in event_registry.get("events", []):
        payload = entry.get("payload_schema")
        if not isinstance(payload, dict) or payload.get("type") != "object" or not payload.get("required"):
            failures.append(f"event payload is not concrete: {entry.get('event_type')}")

    state_machine = load_yaml_file("state_machine.yaml")
    state_names = set(state_machine.get("states", []))
    transitions = list(state_machine.get("forward_transitions", []))
    exceptional = state_machine.get("exceptional_transitions", {})
    transitions.extend(exceptional.get("entries", []) if isinstance(exceptional, dict) else exceptional)
    for transition in transitions:
        transition_from = transition.get("from", transition.get("from_state", "ANY_NONTERMINAL"))
        transition_to = transition.get("to", transition.get("to_state"))
        if transition_from == "ANY_NONTERMINAL":
            continue
        if transition_from not in state_names or transition_to not in state_names:
            failures.append(f"state transition references unknown state: {transition}")
    recovery_sources = {item.get("source_state") for item in state_machine.get("recovery_transitions", [])}
    required_recovery = {"BLOCKED", "INTERRUPTED", "RECOVERY_REQUIRED", "RECONCILIATION_REQUIRED", "INTEGRATION_CONFLICT"}
    if not required_recovery <= recovery_sources:
        failures.append("RecoveryProtocol does not cover every recoverable source state")
    recovery_targets = [item.get("to") for item in state_machine.get("recovery_transitions", [])]
    for item in state_machine.get("recovery_transitions", []):
        recovery_targets.extend(branch.get("to") for branch in item.get("branches", []))
    if "ACCEPTED" in recovery_targets:
        failures.append("RecoveryProtocol may not target ACCEPTED")

    reason_registry = load_yaml_file("reason_code_registry.yaml")
    reason_codes = [item.get("code") for item in reason_registry.get("codes", [])]
    if len(reason_codes) != len(set(reason_codes)):
        failures.append("ReasonCodeRegistry contains duplicate codes")
    namespaces = set(reason_registry.get("namespaces", []))
    if any(item.get("namespace") not in namespaces for item in reason_registry.get("codes", [])):
        failures.append("ReasonCodeRegistry contains an unregistered namespace")

    tool_registry = load_yaml_file("tool_protocol/registry.yaml")
    tools = tool_registry.get("tools", [])
    if len({item.get("tool_name") for item in tools}) != len(tools):
        failures.append("ToolProtocol contains duplicate tool names")
    for item in tools:
        for key in ("request_schema_ref", "result_schema_ref"):
            if not (root / "tool_protocol" / item[key]).is_file():
                failures.append(f"tool schema is unavailable: {item.get('tool_name')}:{item[key]}")
        if not item.get("effect_calculator") or not item.get("resource_calculator"):
            failures.append(f"tool calculators are not registered: {item.get('tool_name')}")

    research = load_yaml_file("research_register.yaml")
    research_ids = [item.get("research_id") for item in research.get("records", [])]
    if len(research_ids) != len(set(research_ids)):
        failures.append("ResearchRegister contains duplicate research_id values")
    allowed_failures = {"UNSUPPORTED", "BLOCKED_CAPABILITY", "DEGRADED_DECLARED"}
    if any(item.get("resolved_value") is None and item.get("failure_behavior") not in allowed_failures for item in research.get("records", [])):
        failures.append("unresolved research record lacks explicit fail-closed behavior")

    persistence = (root / "persistence.sql").read_text(encoding="utf-8")
    for required in ("PRAGMA journal_mode=WAL", "PRAGMA synchronous=FULL", "CREATE TABLE IF NOT EXISTS events", "CREATE TABLE IF NOT EXISTS side_effect_txns"):
        if required not in persistence:
            failures.append(f"PersistenceSchema missing required durability declaration: {required}")

    required_fixture_groups = {"recovery", "resource_normalization", "side_effect_transactions", "repository_identity", "event_payloads", "cli_data_schemas", "research_register"}
    fixture_counts = {p.name: len(list(p.glob("*.json"))) for p in (root / "tests").iterdir() if p.is_dir()} if (root / "tests").is_dir() else {}
    missing_groups = sorted(group for group in required_fixture_groups if group not in fixture_counts or fixture_counts[group] == 0)
    failures.extend(f"missing prescribed fixture group: {group}" for group in missing_groups)
    proofs = {
        "schema_references": not any("schema reference" in failure or "schema fragment" in failure for failure in failures),
        "registries_closed": not any("Registry" in failure or "ToolProtocol" in failure for failure in failures),
        "state_recovery_total": not any("RecoveryProtocol" in failure or "state transition" in failure for failure in failures),
        "event_payloads_concrete": not any("event payload" in failure for failure in failures),
        "durability_declared": not any("PersistenceSchema" in failure for failure in failures),
        "unresolved_external_facts_fail_closed": not any("research record" in failure for failure in failures),
        "fixture_groups_complete": not missing_groups,
    }
    status_value = CommandStatus.SUCCESS if not failures else CommandStatus.INVALID
    _finish(_envelope("contracts check", status_value, "CLI_CONTRACTS_VALID" if not failures else "CONFIG_INVALID", "Contract sources are valid." if not failures else "Contract validation failed.", data={"contract_versions": versions, "fixture_counts": fixture_counts, "failures": failures, "files": files, "proofs": proofs}), json_output)


def main() -> None:
    app()


if __name__ == "__main__":
    sys.exit(main())
