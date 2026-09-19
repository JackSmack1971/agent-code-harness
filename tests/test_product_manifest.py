from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


def _manifest_and_schema(contracts_root: Path) -> tuple[dict, dict]:
    manifest = yaml.safe_load((contracts_root / "product_manifest.yaml").read_text(encoding="utf-8"))
    schema = json.loads((contracts_root / "product_manifest.schema.json").read_text(encoding="utf-8"))
    return manifest, schema


def test_product_manifest_validates_against_its_schema(contracts_root: Path) -> None:
    manifest, schema = _manifest_and_schema(contracts_root)
    Draft202012Validator(schema).validate(manifest)


def test_canonical_product_identity_matches_blueprint(contracts_root: Path) -> None:
    manifest, _ = _manifest_and_schema(contracts_root)
    assert manifest["product_name"] == "Agentic Coding Harness"
    assert manifest["distribution_name"] == "agentic-coding-harness"
    assert manifest["python_import_root"] == "agentic_harness"
    assert manifest["cli_name"] == "harness"
    assert manifest["contract_version"] == 1


def test_python_support_matrix(contracts_root: Path) -> None:
    manifest, _ = _manifest_and_schema(contracts_root)
    assert manifest["python"]["specifier"] == ">=3.13,<3.15"
    assert manifest["python"]["min_inclusive"] == "3.13"
    assert manifest["python"]["max_exclusive"] == "3.15"


def test_git_minimum_version_points_at_a_research_record(contracts_root: Path) -> None:
    manifest, _ = _manifest_and_schema(contracts_root)
    register = yaml.safe_load((contracts_root / "research_register.yaml").read_text(encoding="utf-8"))
    ids = {r["research_id"] for r in register["records"]}
    assert manifest["git"]["minimum_version_research_id"] in ids


def test_build_tooling_matches_blueprint(contracts_root: Path) -> None:
    manifest, _ = _manifest_and_schema(contracts_root)
    build = manifest["build"]
    assert build["build_backend"] == "hatchling"
    assert build["version_source"] == "agentic_harness.__about__.__version__"
    assert build["lock_manager"] == "uv"
    assert build["canonical_lockfile"] == "uv.lock"


def test_malformed_manifest_with_unknown_field_is_rejected(contracts_root: Path) -> None:
    manifest, schema = _manifest_and_schema(contracts_root)
    manifest["unexpected_field"] = "should not be allowed"
    validator = Draft202012Validator(schema)
    assert not validator.is_valid(manifest)


def test_malformed_manifest_missing_required_field_is_rejected(contracts_root: Path) -> None:
    manifest, schema = _manifest_and_schema(contracts_root)
    del manifest["distribution_name"]
    validator = Draft202012Validator(schema)
    assert not validator.is_valid(manifest)
