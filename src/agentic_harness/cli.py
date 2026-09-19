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

from agentic_harness import __version__
from agentic_harness._config import ConfigError, compute_config_digest, resolve_configuration_from_files
from agentic_harness._contracts import find_contracts_root, find_research_record, load_contract_set, load_json
from agentic_harness._identity import uuid7_str
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
    command_file = {"doctor": "doctor", "run": "run", "status": "status", "resume": "resume", "accept": "accept", "reject": "reject", "inspect": "inspect", "config validate": "config_validate", "contracts check": "contracts_check"}.get(envelope["command"])
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


def _open_db(repo: Path, *, create: bool = False) -> sqlite3.Connection:
    path = _db_path(repo)
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE IF NOT EXISTS harness_runs (run_id TEXT PRIMARY KEY, state TEXT NOT NULL, run_version INTEGER NOT NULL, objective TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, reject_reason TEXT)")
    return conn


@app.command()
def run(objective: str | None = typer.Argument(None), objective_file: Path | None = typer.Option(None, "--objective-file"), repo: Path = typer.Option(Path.cwd(), "--repo"), config: Path | None = typer.Option(None, "--config"), json_output: bool = typer.Option(False, "--json")) -> None:
    if (objective is None) == (objective_file is None):
        _finish(_envelope("run", CommandStatus.INVALID, "CLI_INVALID_USAGE", "Provide exactly one objective or --objective-file."), json_output)
    try:
        text_value = objective if objective is not None else objective_file.read_text(encoding="utf-8")
        if not text_value.strip():
            raise ValueError("objective must not be empty")
        run_id = uuid7_str()
        now = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
        conn = _open_db(repo.resolve(), create=True)
        conn.execute("INSERT INTO harness_runs VALUES(?,?,?,?,?,?,?)", (run_id, "CREATED", 0, text_value, now, now, None))
        conn.commit(); conn.close()
        _finish(_envelope("run", CommandStatus.SUCCESS, "CLI_RUN_CREATED", "Run created; execution is ready for the deterministic runtime.", run_id=run_id, state="CREATED", data={"run_id": run_id, "state": "CREATED", "goal_revision_id": None, "blocker": None}), json_output)
    except (OSError, ValueError) as exc:
        _finish(_envelope("run", CommandStatus.INVALID, "CLI_INVALID_USAGE", str(exc)), json_output)


def _get_run(repo: Path, run_id: str) -> tuple[sqlite3.Connection, sqlite3.Row | None]:
    conn = _open_db(repo)
    return conn, conn.execute("SELECT * FROM harness_runs WHERE run_id=?", (run_id,)).fetchone()


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
        conn.execute("UPDATE harness_runs SET state='REJECTED', run_version=run_version+1, reject_reason=? WHERE run_id=?", (reason, run_id)); conn.commit(); code = "CLI_REJECTED"
    conn.close(); _finish(_envelope("reject", CommandStatus.SUCCESS, code, "Run rejected.", run_id=run_id, state="REJECTED", data={"terminal_state": "REJECTED", "reason_artifact": None}), json_output)


@app.command()
def accept(run_id: str, strategy: str = typer.Option("squash", "--strategy"), repo: Path = typer.Option(Path.cwd(), "--repo"), json_output: bool = typer.Option(False, "--json")) -> None:
    if strategy not in {"squash", "cherry-pick", "fast-forward", "patch-only"}:
        _finish(_envelope("accept", CommandStatus.INVALID, "CLI_INVALID_USAGE", "Unsupported integration strategy."), json_output)
    conn, row = _get_run(repo.resolve(), run_id)
    if row is None:
        conn.close(); _finish(_envelope("accept", CommandStatus.INVALID, "CLI_RUN_NOT_FOUND", "Run was not found.", run_id=run_id), json_output)
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
    for path in sorted(root.rglob("*.schema.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(document)
            if "x-contract-name" in document:
                versions[document["x-contract-name"]] = document.get("x-contract-version", 0)
        except Exception as exc:
            failures.append(f"{path.relative_to(root)}: {exc}")
    for path in sorted(root.glob("*.yaml")):
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:
            failures.append(f"{path.relative_to(root)}: {exc}")
    fixture_counts = {p.name: len(list(p.glob("*.json"))) for p in (root / "tests").iterdir() if p.is_dir()} if (root / "tests").is_dir() else {}
    status_value = CommandStatus.SUCCESS if not failures else CommandStatus.INVALID
    _finish(_envelope("contracts check", status_value, "CLI_CONTRACTS_VALID" if not failures else "CONFIG_INVALID", "Contract sources are valid." if not failures else "Contract validation failed.", data={"contract_versions": versions, "fixture_counts": fixture_counts, "failures": failures, "files": files}), json_output)


def main() -> None:
    app()


if __name__ == "__main__":
    sys.exit(main())
