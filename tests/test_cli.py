from __future__ import annotations

import json

from typer.testing import CliRunner

from agentic_harness.cli import app

runner = CliRunner()


def test_doctor_starts_and_exits_success() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0, result.output


def test_doctor_json_envelope_matches_cli_protocol_shape() -> None:
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0, result.output
    envelope = json.loads(result.output)
    assert envelope["protocol"] == "harness.cli"
    assert envelope["protocol_version"] == 1
    assert envelope["command"] == "doctor"
    assert envelope["status"] == "SUCCESS"
    assert envelope["data"] is not None
    checks = {c["capability"]: c for c in envelope["data"]["checks"]}
    assert "PYTHON_RUNTIME" in checks
    assert "GIT_MIN_VERSION" in checks
    assert "GIT_SHA256_REPOSITORY_SUPPORT" in checks
    # Never guessed: SHA-256 dual-format support is not yet proven.
    assert checks["GIT_SHA256_REPOSITORY_SUPPORT"]["status"] in ("UNSUPPORTED", "BLOCKED_CAPABILITY")


def test_doctor_reports_supported_python_runtime() -> None:
    result = runner.invoke(app, ["doctor", "--json"])
    envelope = json.loads(result.output)
    checks = {c["capability"]: c for c in envelope["data"]["checks"]}
    assert checks["PYTHON_RUNTIME"]["status"] == "SUPPORTED"


def test_help_starts_without_error() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
