"""`harness` CLI entry point.

Phase 0A scope: only `harness doctor` exists. It performs read-only capability
detection (installed Python, system Git) and reports each capability's
support status. It never mutates Git state, configuration, or persistence.
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from typing import Any

import typer

from agentic_harness import __version__
from agentic_harness._contracts import find_research_record, load_contract_set
from agentic_harness._reason_codes import CommandStatus, ExitClass
from agentic_harness._versioning import at_least, below

app = typer.Typer(
    name="harness",
    help="Agentic Coding Harness CLI.",
    no_args_is_help=True,
    add_completion=False,
)


def _check_python(manifest: dict[str, Any]) -> dict[str, Any]:
    python_cfg = manifest["python"]
    actual = platform.python_version()
    supported = at_least(actual, python_cfg["min_inclusive"]) and below(actual, python_cfg["max_exclusive"])
    return {
        "capability": "PYTHON_RUNTIME",
        "status": "SUPPORTED" if supported else "UNSUPPORTED",
        "observed_version": actual,
        "required_specifier": python_cfg["specifier"],
    }


def _check_git(register: list[dict[str, Any]]) -> dict[str, Any]:
    record = find_research_record(register, "GIT_MIN_VERSION")
    git_path = shutil.which("git")
    if git_path is None:
        return {
            "capability": "GIT_MIN_VERSION",
            "status": "BLOCKED_CAPABILITY",
            "reason": "system git executable not found on PATH",
        }
    proc = subprocess.run([git_path, "--version"], capture_output=True, text=True, check=False, timeout=10)
    observed = proc.stdout.strip() if proc.returncode == 0 else None
    if observed is None or record is None or record.get("resolved_value") is None:
        return {
            "capability": "GIT_MIN_VERSION",
            "status": "BLOCKED_CAPABILITY",
            "observed_version": observed,
            "reason": "research record unresolved or git invocation failed",
        }
    minimum = record["resolved_value"]
    supported = at_least(observed, minimum)
    return {
        "capability": "GIT_MIN_VERSION",
        "status": "SUPPORTED" if supported else "UNSUPPORTED",
        "observed_version": observed,
        "required_minimum": minimum,
        "source_refs": record.get("source_refs", []),
    }


def _check_sha256(register: list[dict[str, Any]]) -> dict[str, Any]:
    record = find_research_record(register, "GIT_SHA256_REPOSITORY_SUPPORT")
    failure_behavior = record["failure_behavior"] if record else "BLOCKED_CAPABILITY"
    return {
        "capability": "GIT_SHA256_REPOSITORY_SUPPORT",
        "status": failure_behavior,
        "reason": "doctor capability detection across both object formats has not been proven; "
        "the implementation MUST NOT infer OID length globally",
    }


@app.command()
def version() -> None:
    """Print the installed harness version."""
    typer.echo(__version__)
    raise typer.Exit(code=int(ExitClass.SUCCESS))


@app.command()
def doctor(json_output: bool = typer.Option(False, "--json", help="Emit the machine-readable result envelope.")) -> None:
    """Report support status for capabilities gating harness operation."""
    contracts = load_contract_set()
    if contracts is None:
        envelope = {
            "protocol": "harness.cli",
            "protocol_version": 1,
            "command": "doctor",
            "status": CommandStatus.UNSUPPORTED,
            "symbolic_code": "CONTRACTS_ROOT_NOT_FOUND",
            "run_id": None,
            "state": None,
            "message": "Could not locate the canonical contracts/ directory.",
            "data": None,
        }
        _emit(envelope, json_output)
        raise typer.Exit(code=int(ExitClass.UNSUPPORTED_CAPABILITY))

    checks = [
        _check_python(contracts.product_manifest),
        _check_git(contracts.research_register),
        _check_sha256(contracts.research_register),
    ]
    any_unsupported = any(c["status"] in ("UNSUPPORTED", "BLOCKED_CAPABILITY") for c in checks)
    envelope = {
        "protocol": "harness.cli",
        "protocol_version": 1,
        "command": "doctor",
        "status": CommandStatus.SUCCESS,
        "symbolic_code": "DOCTOR_REPORT_UNSUPPORTED_PRESENT" if any_unsupported else "DOCTOR_REPORT_ALL_SUPPORTED",
        "run_id": None,
        "state": None,
        "message": "Capability report generated." if not any_unsupported else "One or more capabilities are unsupported or blocked.",
        "data": {"checks": checks, "contracts_root": str(contracts.root)},
    }
    _emit(envelope, json_output)
    raise typer.Exit(code=int(ExitClass.SUCCESS))


def _emit(envelope: dict[str, Any], json_output: bool) -> None:
    if json_output:
        typer.echo(json.dumps(envelope, indent=2, sort_keys=True))
        return
    typer.echo(f"harness doctor: {envelope['status']} ({envelope['symbolic_code']})")
    for check in (envelope["data"] or {}).get("checks", []):
        line = f"  - {check['capability']}: {check['status']}"
        if "observed_version" in check and check["observed_version"]:
            line += f" (observed {check['observed_version']})"
        typer.echo(line)


def main() -> None:
    app()


if __name__ == "__main__":
    sys.exit(main())
