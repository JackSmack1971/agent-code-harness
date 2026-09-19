from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from agentic_harness import _config
from agentic_harness._config import (
    ConfigAliasConflictError,
    ConfigError,
    apply_env_overrides,
    apply_security_monotonicity,
    compute_config_digest,
    canonical_config_paths,
    merge_layers,
    migrate_aliases,
    parse_toml_bytes,
    resolve_configuration,
    resolve_configuration_from_files,
)

FIXTURES_DIR_NAME = "configuration_schema"


def _schema_doc(contracts_root: Path) -> dict[str, Any]:
    return json.loads((contracts_root / "configuration_schema.schema.json").read_text(encoding="utf-8"))


def _semantic_types_doc(contracts_root: Path) -> dict[str, Any]:
    return json.loads((contracts_root / "semantic_types.schema.json").read_text(encoding="utf-8"))


def _registry(contracts_root: Path) -> tuple[Registry, dict[str, Any]]:
    cfg = _schema_doc(contracts_root)
    sem = _semantic_types_doc(contracts_root)
    registry = Registry().with_resources([(sem["$id"], Resource.from_contents(sem)), (cfg["$id"], Resource.from_contents(cfg))])
    return registry, cfg


def _validator_for(defname: str, contracts_root: Path) -> Draft202012Validator:
    registry, cfg = _registry(contracts_root)
    return Draft202012Validator({"$ref": f"{cfg['$id']}#/$defs/{defname}"}, registry=registry)


def _load_fixture(contracts_root: Path, name: str) -> list[dict[str, Any]]:
    path = contracts_root / "tests" / FIXTURES_DIR_NAME / name
    return json.loads(path.read_text(encoding="utf-8"))


def _golden_cases(contracts_root: Path) -> list[tuple[str, Any]]:
    return [(c["def"], c["value"]) for c in _load_fixture(contracts_root, "golden.json")]


def _adversarial_cases(contracts_root: Path) -> list[tuple[str, Any]]:
    return [(c["def"], c["value"]) for c in _load_fixture(contracts_root, "adversarial.json")]


_CONTRACTS_ROOT = Path(__file__).resolve().parents[1] / "contracts"


# ---------------------------------------------------------------------------
# Contract structural conformance
# ---------------------------------------------------------------------------


def test_schema_is_valid_draft_2020_12(contracts_root: Path) -> None:
    Draft202012Validator.check_schema(_schema_doc(contracts_root))


def test_registry_yaml_validates_against_its_schema(contracts_root: Path) -> None:
    doc = _config.load_registry(contracts_root)
    assert doc["x-contract-name"] == "ConfigurationSchema"


def test_fixture_files_exist(contracts_root: Path) -> None:
    assert (contracts_root / "tests" / FIXTURES_DIR_NAME / "golden.json").is_file()
    assert (contracts_root / "tests" / FIXTURES_DIR_NAME / "adversarial.json").is_file()


def test_canonical_top_level_keys_match_blueprint_9_9_2(contracts_root: Path) -> None:
    doc = _config.load_registry(contracts_root)
    assert doc["canonical_top_level_keys"] == [
        "runtime", "workspace", "sandbox", "policy", "providers", "routes", "context",
        "retrieval", "verification", "repository_commands", "network", "data_egress",
        "secrets", "parsers", "memory", "skills", "events", "telemetry", "retention",
        "approvals", "acceptance", "mcp", "doctor", "extensions",
    ]


def test_aliases_are_exactly_run_and_routing(contracts_root: Path) -> None:
    doc = _config.load_registry(contracts_root)
    assert doc["aliases"] == {"run": "runtime", "routing": "routes"}


def test_precedence_order_matches_blueprint_9_9_1(contracts_root: Path) -> None:
    doc = _config.load_registry(contracts_root)
    assert doc["precedence_order"] == [
        "built_in_defaults", "system_config", "user_config", "repository_config",
        "explicit_config_file", "environment_overrides", "cli_overrides",
    ]


def test_env_overrides_registry_matches_blueprint_10_6_2(contracts_root: Path) -> None:
    doc = _config.load_registry(contracts_root)
    variables = {entry["variable"] for entry in doc["env_overrides"]}
    assert variables == {
        "HARNESS_CONFIG", "HARNESS_LOG_LEVEL", "HARNESS_JSON",
        "HARNESS_PROVIDER_OPENAI_KEY", "HARNESS_PROVIDER_ANTHROPIC_KEY", "HARNESS_PROVIDER_OPENROUTER_KEY",
    }


@pytest.mark.parametrize("defname,value", _golden_cases(_CONTRACTS_ROOT))
def test_golden_values_validate(defname: str, value: Any, contracts_root: Path) -> None:
    validator = _validator_for(defname, contracts_root)
    errors = sorted(validator.iter_errors(value), key=str)
    assert not errors, f"{defname}: {[e.message for e in errors]}"


@pytest.mark.parametrize("defname,value", _adversarial_cases(_CONTRACTS_ROOT))
def test_adversarial_values_are_rejected(defname: str, value: Any, contracts_root: Path) -> None:
    validator = _validator_for(defname, contracts_root)
    assert not validator.is_valid(value), f"{defname}: {value!r} unexpectedly validated"


# ---------------------------------------------------------------------------
# TOML parsing
# ---------------------------------------------------------------------------


def test_parse_toml_bytes_parses_a_simple_document() -> None:
    doc = parse_toml_bytes(b'[runtime]\nheadless = true\n')
    assert doc == {"runtime": {"headless": True}}


def test_parse_toml_bytes_rejects_invalid_toml() -> None:
    with pytest.raises(ConfigError):
        parse_toml_bytes(b"this is not [ valid toml")


def test_canonical_config_paths_match_linux_contract(tmp_path: Path) -> None:
    paths = canonical_config_paths("linux", tmp_path / "repo", env={"XDG_CONFIG_HOME": str(tmp_path / "xdg")}, home=tmp_path / "home")
    assert paths["system"] == (Path("/etc/agentic-harness/config.toml"),)
    assert paths["user"][0] == tmp_path / "xdg" / "agentic-harness" / "config.toml"
    assert paths["repository"] == (tmp_path / "repo" / ".harness" / "config.toml",)


def test_resolve_configuration_from_files_honors_harness_config(tmp_path: Path, contracts_root: Path) -> None:
    explicit = tmp_path / "explicit.toml"
    explicit.write_text("[runtime]\nlog_level = 'DEBUG'\n", encoding="utf-8")
    cfg = resolve_configuration_from_files(
        platform="linux", repository_root=tmp_path / "repo", env={"HARNESS_CONFIG": str(explicit)},
        contracts_root=contracts_root, home=tmp_path / "home",
    )
    assert cfg["runtime"]["log_level"] == "DEBUG"


def test_resolve_configuration_from_files_missing_explicit_config_fails(tmp_path: Path, contracts_root: Path) -> None:
    with pytest.raises(ConfigError):
        resolve_configuration_from_files(
            platform="linux", repository_root=tmp_path / "repo", env={"HARNESS_CONFIG": str(tmp_path / "missing.toml")},
            contracts_root=contracts_root, home=tmp_path / "home",
        )


# ---------------------------------------------------------------------------
# Alias migration (9.9.2/10.6)
# ---------------------------------------------------------------------------


ALIASES = {"run": "runtime", "routing": "routes"}


def test_migrate_aliases_rewrites_alias_key() -> None:
    out = migrate_aliases({"run": {"headless": True}}, ALIASES)
    assert out == {"runtime": {"headless": True}}


def test_migrate_aliases_passes_through_canonical_key() -> None:
    out = migrate_aliases({"runtime": {"headless": True}}, ALIASES)
    assert out == {"runtime": {"headless": True}}


def test_migrate_aliases_rejects_alias_and_canonical_together() -> None:
    with pytest.raises(ConfigAliasConflictError):
        migrate_aliases({"run": {}, "runtime": {}}, ALIASES)


def test_migrate_aliases_rejects_routing_and_routes_together() -> None:
    with pytest.raises(ConfigAliasConflictError):
        migrate_aliases({"routing": {}, "routes": {}}, ALIASES)


# ---------------------------------------------------------------------------
# Ordinary precedence merge (9.9.1)
# ---------------------------------------------------------------------------


def test_merge_layers_higher_precedence_overrides_lower() -> None:
    merged = merge_layers([
        ("built_in_defaults", {"runtime": {"headless": False, "log_level": "INFO"}}),
        ("user_config", {"runtime": {"headless": True}}),
    ])
    assert merged["runtime"] == {"headless": True, "log_level": "INFO"}


def test_merge_layers_does_not_mutate_unrelated_sections() -> None:
    merged = merge_layers([
        ("built_in_defaults", {"runtime": {"headless": False}, "workspace": {"root": None}}),
        ("user_config", {"runtime": {"headless": True}}),
    ])
    assert merged["workspace"] == {"root": None}


def test_merge_layers_security_fields_cannot_be_widened_by_precedence() -> None:
    merged = merge_layers([
        ("system_config", {"network": {"default": "deny"}}),
        ("explicit_config_file", {"network": {"default": "allow"}}),
    ])
    assert merged["network"]["default"] == "deny"


# ---------------------------------------------------------------------------
# Environment overrides (10.6.2)
# ---------------------------------------------------------------------------


def _registry_doc() -> dict[str, Any]:
    return _config.load_registry(_CONTRACTS_ROOT)


def test_apply_env_overrides_only_applies_registered_variables() -> None:
    base = {"runtime": {"log_level": "INFO"}}
    result = apply_env_overrides(base, {"HARNESS_LOG_LEVEL": "DEBUG", "HARNESS_UNREGISTERED": "x"}, _registry_doc()["env_overrides"])
    assert result["runtime"]["log_level"] == "DEBUG"


def test_apply_env_overrides_secret_reference_never_carries_plaintext() -> None:
    base = {"providers": {}}
    result = apply_env_overrides(base, {"HARNESS_PROVIDER_OPENAI_KEY": "sk-super-secret-value"}, _registry_doc()["env_overrides"])
    api_key = result["providers"]["openai"]["api_key"]
    assert api_key == {"source": "env", "name": "HARNESS_PROVIDER_OPENAI_KEY"}
    assert "sk-super-secret-value" not in json.dumps(result)


def test_apply_env_overrides_ignores_config_file_path_kind() -> None:
    base = {"runtime": {"log_level": "INFO"}}
    result = apply_env_overrides(base, {"HARNESS_CONFIG": "/some/path.toml"}, _registry_doc()["env_overrides"])
    assert result == base


# ---------------------------------------------------------------------------
# Security monotonicity (9.9.1/9.12.4/10.6.1): repository config narrows only
# ---------------------------------------------------------------------------


def test_apply_security_monotonicity_cannot_relax_require_non_root() -> None:
    higher = {"sandbox": {"require_non_root": True}}
    proposed = {"sandbox": {"require_non_root": False}}
    narrowed = apply_security_monotonicity(higher, proposed)
    assert narrowed["sandbox"]["require_non_root"] is True


def test_apply_security_monotonicity_cannot_widen_network_default_to_allow() -> None:
    higher = {"network": {"default": "deny"}}
    proposed = {"network": {"default": "allow"}}
    narrowed = apply_security_monotonicity(higher, proposed)
    assert narrowed["network"]["default"] == "deny"


def test_apply_security_monotonicity_can_narrow_network_default_further() -> None:
    higher = {"network": {"default": "allow"}}
    proposed = {"network": {"default": "deny"}}
    narrowed = apply_security_monotonicity(higher, proposed)
    assert narrowed["network"]["default"] == "deny"


def test_apply_security_monotonicity_intersects_allowed_origins() -> None:
    higher = {"network": {"allowed_origins": ["https://api.example.com"]}}
    proposed = {"network": {"allowed_origins": ["https://api.example.com", "https://evil.example.com"]}}
    narrowed = apply_security_monotonicity(higher, proposed)
    assert narrowed["network"]["allowed_origins"] == ["https://api.example.com"]


def test_apply_security_monotonicity_cannot_raise_data_egress_ceiling() -> None:
    higher = {"data_egress": {"maximum_classification": "PUBLIC"}}
    proposed = {"data_egress": {"maximum_classification": "SECRET"}}
    narrowed = apply_security_monotonicity(higher, proposed)
    assert narrowed["data_egress"]["maximum_classification"] == "PUBLIC"


# ---------------------------------------------------------------------------
# Full resolution pipeline + ConfigDigest (9.9.5)
# ---------------------------------------------------------------------------


def test_resolve_configuration_with_no_sources_yields_the_built_in_defaults(contracts_root: Path) -> None:
    cfg = resolve_configuration(system_document=None, user_document=None, repository_document=None, explicit_document=None, env={}, contracts_root=contracts_root)
    assert cfg == _config.load_registry(contracts_root)["required_defaults"]


def test_resolve_configuration_rejects_unknown_top_level_key(contracts_root: Path) -> None:
    with pytest.raises(ConfigError):
        resolve_configuration(system_document=None, user_document=None, repository_document={"bogus": {}}, explicit_document=None, env={}, contracts_root=contracts_root)


def test_resolve_configuration_rejects_alias_conflict_across_sources(contracts_root: Path) -> None:
    with pytest.raises(ConfigAliasConflictError):
        resolve_configuration(
            system_document={"run": {"headless": True}},
            user_document={"runtime": {"log_level": "DEBUG"}},
            repository_document=None, explicit_document=None, env={}, contracts_root=contracts_root,
        )


def test_resolve_configuration_migrates_run_alias_to_runtime(contracts_root: Path) -> None:
    cfg = resolve_configuration(system_document=None, user_document=None, repository_document={"run": {"headless": True}}, explicit_document=None, env={}, contracts_root=contracts_root)
    assert cfg["runtime"]["headless"] is True


def test_resolve_configuration_repository_layer_cannot_widen_higher_authority_security(contracts_root: Path) -> None:
    system_document = {"sandbox": {"require_non_root": True}}
    repository_document = {"sandbox": {"require_non_root": False}}
    cfg = resolve_configuration(
        system_document=system_document, user_document=None, repository_document=repository_document,
        explicit_document=None, env={}, contracts_root=contracts_root,
    )
    assert cfg["sandbox"]["require_non_root"] is True


def test_resolve_configuration_explicit_layer_cannot_widen_system_network_deny(contracts_root: Path) -> None:
    cfg = resolve_configuration(
        system_document={"network": {"default": "deny"}}, user_document=None,
        repository_document=None, explicit_document={"network": {"default": "allow"}},
        env={}, contracts_root=contracts_root,
    )
    assert cfg["network"]["default"] == "deny"


def test_resolve_configuration_cli_layer_cannot_raise_egress_ceiling(contracts_root: Path) -> None:
    cfg = resolve_configuration(
        system_document={"data_egress": {"maximum_classification": "PUBLIC"}}, user_document=None,
        repository_document=None, explicit_document=None, env={},
        cli_overrides={"data_egress": {"maximum_classification": "SECRET"}},
        contracts_root=contracts_root,
    )
    assert cfg["data_egress"]["maximum_classification"] == "PUBLIC"


def test_resolve_configuration_is_deterministic_and_digest_stable(contracts_root: Path) -> None:
    cfg_a = resolve_configuration(system_document=None, user_document=None, repository_document=None, explicit_document=None, env={}, contracts_root=contracts_root)
    cfg_b = resolve_configuration(system_document=None, user_document=None, repository_document=None, explicit_document=None, env={}, contracts_root=contracts_root)
    assert compute_config_digest(cfg_a) == compute_config_digest(cfg_b)


def test_config_digest_changes_when_effective_configuration_changes(contracts_root: Path) -> None:
    cfg_a = resolve_configuration(system_document=None, user_document=None, repository_document=None, explicit_document=None, env={}, contracts_root=contracts_root)
    cfg_b = resolve_configuration(system_document={"runtime": {"log_level": "DEBUG"}}, user_document=None, repository_document=None, explicit_document=None, env={}, contracts_root=contracts_root)
    assert compute_config_digest(cfg_a) != compute_config_digest(cfg_b)


def test_config_digest_excludes_secret_plaintext_because_none_is_ever_present(contracts_root: Path) -> None:
    cfg = resolve_configuration(
        system_document=None, user_document=None, repository_document=None, explicit_document=None,
        env={"HARNESS_PROVIDER_OPENAI_KEY": "sk-do-not-leak-this"}, contracts_root=contracts_root,
    )
    digest = compute_config_digest(cfg)
    assert isinstance(digest, str) and digest.startswith("sha256:")
    assert "sk-do-not-leak-this" not in json.dumps(cfg)


def test_config_digest_rejects_plaintext_secret_configuration() -> None:
    with pytest.raises(ConfigError):
        compute_config_digest({"providers": {"openai": {"api_key": "plaintext"}}})
