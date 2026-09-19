"""`ConfigurationSchema v1` reference implementation (Blueprint 9.9, 10.6).

`contracts/configuration_schema.schema.json` / `.yaml` is the sole
authoritative source for the canonical top-level tree, migration aliases,
ordinary precedence order, canonical file locations, registered
environment overrides, required fail-safe defaults, and the secret-source
registry; this module is the executable parse/migrate/merge/validate/digest
pipeline that document describes, not a second hand-maintained copy
(Canonical Identity Rules). TOML is the sole operator-authored file format
(9.9.1); parsing uses the standard-library `tomllib` (read-only, matching
"operator-authored", never machine-written back out).
"""

from __future__ import annotations

import copy
import tomllib
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from ._canonical import CanonicalizationError, digest_for
from ._classification import classification_order, classification_rank
from ._contracts import find_contracts_root, load_json, load_yaml

REASON_CODE_CONFIG_INVALID = "CONFIG_INVALID"
REASON_CODE_CONFIG_UNKNOWN_KEY = "CONFIG_UNKNOWN_KEY"
REASON_CODE_CONFIG_ALIAS_CONFLICT = "CONFIG_ALIAS_CONFLICT"

# 9.9.1, lowest to highest. Security authority is NOT this ordering (9.12.4).
PRECEDENCE_ORDER: tuple[str, ...] = (
    "built_in_defaults", "system_config", "user_config", "repository_config",
    "explicit_config_file", "environment_overrides", "cli_overrides",
)

# Security-relevant EffectiveConfiguration fields use monotonic intersection
# across supplied security-bearing layers (10.6.1). Field kind drives which
# narrowing rule applies.
_NARROW_ONLY_BOOL_STRICTER_TRUE = (
    ("sandbox", "require_non_root"),
    ("sandbox", "require_isolation"),
    ("workspace", "preserve_original_checkout"),
    ("acceptance", "require_destination_reconciliation"),
    ("acceptance", "require_post_integration_verification"),
    ("policy", "repository_text_can_expand_authority"),
)
_NARROW_ONLY_DENY_WINS = (
    ("network", "default"),
    ("data_egress", "default"),
)
_NARROW_ONLY_ALLOWLIST_INTERSECT = (
    ("network", "allowed_origins"),
)
_NARROW_ONLY_CLASSIFICATION_CEILING = (
    ("data_egress", "maximum_classification"),
)


class ConfigError(ValueError):
    def __init__(self, message: str, *, reason_code: str = REASON_CODE_CONFIG_INVALID) -> None:
        super().__init__(message)
        self.reason_code = reason_code


class ConfigAliasConflictError(ConfigError):
    def __init__(self, message: str) -> None:
        super().__init__(message, reason_code=REASON_CODE_CONFIG_ALIAS_CONFLICT)


# ---------------------------------------------------------------------------
# Registry loading
# ---------------------------------------------------------------------------


def load_registry(contracts_root: Path | None = None) -> dict[str, Any]:
    root = contracts_root or find_contracts_root()
    if root is None:
        raise ConfigError("contracts/ root not found; cannot resolve configuration without the authoritative registry")
    return load_yaml(root / "configuration_schema.yaml")


def _effective_configuration_validator(contracts_root: Path | None = None) -> Draft202012Validator:
    root = contracts_root or find_contracts_root()
    if root is None:
        raise ConfigError("contracts/ root not found")
    schema_doc = load_json(root / "configuration_schema.schema.json")
    semantic_doc = load_json(root / "semantic_types.schema.json")
    registry = Registry().with_resources([
        (semantic_doc["$id"], Resource.from_contents(semantic_doc)),
        (schema_doc["$id"], Resource.from_contents(schema_doc)),
    ])
    ref = f"{schema_doc['$id']}#/$defs/EffectiveConfiguration"
    return Draft202012Validator({"$ref": ref}, registry=registry)


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------


def parse_toml_bytes(data: bytes) -> dict[str, Any]:
    try:
        return tomllib.loads(data.decode("utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"configuration file is not valid TOML: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise ConfigError(f"configuration file is not valid UTF-8: {exc}") from exc


def parse_toml_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"explicit configuration file not found: {path}")
    return parse_toml_bytes(path.read_bytes())


def canonical_config_paths(
    platform: str,
    repository_root: Path,
    *,
    env: dict[str, str] | None = None,
    home: Path | None = None,
) -> dict[str, tuple[Path, ...]]:
    """Return the exact implicit configuration locations for one platform.

    The returned paths are ordered only where the contract defines a fallback
    (Linux user configuration). Existence is deliberately not required here;
    callers decide whether a missing path is implicit or explicit.
    """
    values = env or {}
    home_path = home or Path.home()
    if platform == "linux":
        fallback = home_path / ".config" / "agentic-harness" / "config.toml"
        primary = (Path(values["XDG_CONFIG_HOME"]) / "agentic-harness" / "config.toml") if values.get("XDG_CONFIG_HOME") else fallback
        user_paths = (primary,) if primary == fallback else (primary, fallback)
        return {
            "system": (Path("/etc/agentic-harness/config.toml"),),
            "user": user_paths,
            "repository": (repository_root / ".harness" / "config.toml",),
        }
    if platform == "macos":
        return {
            "system": (Path("/Library/Application Support/Agentic Harness/config.toml"),),
            "user": (home_path / "Library" / "Application Support" / "Agentic Harness" / "config.toml",),
            "repository": (repository_root / ".harness" / "config.toml",),
        }
    if platform == "windows":
        try:
            program_data = Path(values["PROGRAMDATA"])
            app_data = Path(values["APPDATA"])
        except KeyError as exc:
            raise ConfigError(f"missing required Windows configuration location environment variable: {exc.args[0]}") from exc
        return {
            "system": (program_data / "AgenticHarness" / "config.toml",),
            "user": (app_data / "AgenticHarness" / "config.toml",),
            "repository": (repository_root / ".harness" / "config.toml",),
        }
    raise ConfigError(f"unsupported configuration platform: {platform!r}")


def resolve_configuration_from_files(
    *,
    platform: str,
    repository_root: Path,
    env: dict[str, str],
    cli_overrides: dict[str, Any] | None = None,
    explicit_path: Path | None = None,
    home: Path | None = None,
    contracts_root: Path | None = None,
) -> dict[str, Any]:
    """Load implicit TOML sources and resolve them under ConfigurationSchema v1."""
    paths = canonical_config_paths(platform, repository_root, env=env, home=home)

    def optional_document(candidates: tuple[Path, ...]) -> dict[str, Any] | None:
        for candidate in candidates:
            if candidate.is_file():
                return parse_toml_file(candidate)
        return None

    configured_explicit = explicit_path
    if configured_explicit is None and env.get("HARNESS_CONFIG"):
        configured_explicit = Path(env["HARNESS_CONFIG"])
    explicit_document = parse_toml_file(configured_explicit) if configured_explicit is not None else None

    return resolve_configuration(
        system_document=optional_document(paths["system"]),
        user_document=optional_document(paths["user"]),
        repository_document=optional_document(paths["repository"]),
        explicit_document=explicit_document,
        env=env,
        cli_overrides=cli_overrides,
        contracts_root=contracts_root,
    )


# ---------------------------------------------------------------------------
# Alias migration (9.9.2/10.6)
# ---------------------------------------------------------------------------


def migrate_aliases(document: dict[str, Any], aliases: dict[str, str]) -> dict[str, Any]:
    """Rewrite alias top-level keys to their canonical form for one source document.

    Alias and canonical key present together in the same document is
    CONFIG_ALIAS_CONFLICT (9.9.2: "Alias and canonical key appearing
    together is invalid").
    """
    migrated = dict(document)
    for alias, canonical in aliases.items():
        if alias not in migrated:
            continue
        if canonical in document:
            raise ConfigAliasConflictError(
                f"configuration document sets both alias key {alias!r} and its canonical key {canonical!r}"
            )
        migrated[canonical] = migrated.pop(alias)
    return migrated


def check_cross_source_alias_conflict(documents: list[tuple[str, dict[str, Any]]], aliases: dict[str, str]) -> None:
    """9.9.2/10.6: "canonical and alias forms appearing together are invalid"
    applies across the whole set of sources being resolved together, not
    only within a single document — an operator setting `run.headless` in
    system config and `runtime.log_level` in user config is exactly the
    ambiguous case the rule exists to catch (which alias-user's intent
    should win is not decidable). Per-document conflicts are caught first
    (and more specifically) by `migrate_aliases`; this catches the
    cross-document case that a per-document check cannot see.
    """
    key_sources: dict[str, tuple[str, str]] = {}  # canonical_key -> (layer_name, key_as_written)
    for layer_name, document in documents:
        for key in document:
            canonical = aliases.get(key, key)
            if canonical not in key_sources:
                key_sources[canonical] = (layer_name, key)
                continue
            prior_layer, prior_key = key_sources[canonical]
            if prior_key != key:
                raise ConfigAliasConflictError(
                    f"{prior_layer!r} sets {prior_key!r} while {layer_name!r} sets {key!r}; both resolve to "
                    f"the same logical key {canonical!r} via conflicting alias/canonical forms"
                )


def validate_top_level_keys(document: dict[str, Any], canonical_top_level_keys: list[str]) -> None:
    unknown = set(document) - set(canonical_top_level_keys)
    if unknown:
        raise ConfigError(
            f"configuration document has unrecognized top-level key(s): {sorted(unknown)}",
            reason_code=REASON_CODE_CONFIG_UNKNOWN_KEY,
        )


# ---------------------------------------------------------------------------
# Merge (ordinary precedence, 9.9.1)
# ---------------------------------------------------------------------------


def _deep_merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            merged[key] = _deep_merge(base.get(key), value) if key in base else value
        return merged
    return copy.deepcopy(override)


def merge_layers(layers: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    """Merge layers while preserving security intersection semantics.

    Ordinary fields use last-writer-wins precedence. Security fields use the
    first explicit constraint as the baseline and every subsequent layer can
    only narrow it; built-in defaults are fallback values, not an authority
    that prevents explicit operator configuration.
    """
    result: dict[str, Any] = {}
    security_authority: dict[str, Any] = {}
    for layer_name, document in layers:
        effective_document = document
        if layer_name != "built_in_defaults" and security_authority:
            effective_document = apply_security_monotonicity(security_authority, document)
        result = _deep_merge(result, effective_document)
        if layer_name != "built_in_defaults":
            security_authority = _deep_merge(security_authority, effective_document)
    return result


# ---------------------------------------------------------------------------
# Security monotonicity (9.9.1/9.12.4/10.6.1): later security-bearing layers
# may narrow, never widen, earlier security constraints.
# ---------------------------------------------------------------------------


def apply_security_monotonicity(higher_authority: dict[str, Any], repository_layer: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of `repository_layer` with every security-relevant field
    clamped so it can only narrow, never widen, `higher_authority`'s
    effective value for that field. Non-security-relevant fields pass
    through unchanged (ordinary precedence still governs those).
    """
    narrowed = copy.deepcopy(repository_layer)

    for section, field in _NARROW_ONLY_BOOL_STRICTER_TRUE:
        higher_value = _get_path(higher_authority, section, field)
        proposed_value = _get_path(narrowed, section, field)
        if higher_value is None or proposed_value is None:
            continue
        _set_path(narrowed, section, field, bool(higher_value) or bool(proposed_value))

    for section, field in _NARROW_ONLY_DENY_WINS:
        higher_value = _get_path(higher_authority, section, field)
        proposed_value = _get_path(narrowed, section, field)
        if higher_value is None or proposed_value is None:
            continue
        _set_path(narrowed, section, field, "deny" if "deny" in (higher_value, proposed_value) else proposed_value)

    for section, field in _NARROW_ONLY_ALLOWLIST_INTERSECT:
        higher_value = _get_path(higher_authority, section, field)
        proposed_value = _get_path(narrowed, section, field)
        if higher_value is None or proposed_value is None:
            continue
        _set_path(narrowed, section, field, [item for item in proposed_value if item in higher_value])

    for section, field in _NARROW_ONLY_CLASSIFICATION_CEILING:
        higher_value = _get_path(higher_authority, section, field)
        proposed_value = _get_path(narrowed, section, field)
        if higher_value is None or proposed_value is None:
            continue
        order = classification_order()
        ceiling = order[min(classification_rank(higher_value), classification_rank(proposed_value))]
        _set_path(narrowed, section, field, ceiling)

    return narrowed


def _get_path(document: dict[str, Any], section: str, field: str) -> Any:
    return document.get(section, {}).get(field) if isinstance(document.get(section), dict) else None


def _set_path(document: dict[str, Any], section: str, field: str, value: Any) -> None:
    document.setdefault(section, {})[field] = value


# ---------------------------------------------------------------------------
# Environment overrides (10.6.2)
# ---------------------------------------------------------------------------


def apply_env_overrides(config: dict[str, Any], env: dict[str, str], env_overrides: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply only the registered environment-variable overrides (10.6.2).

    Environment variables are disabled by default except this registry; an
    unregistered `HARNESS_*` variable in `env` is never consulted.
    """
    result = copy.deepcopy(config)
    for entry in env_overrides:
        variable = entry["variable"]
        if variable not in env:
            continue
        if entry["kind"] == "CONFIG_FILE_PATH":
            continue  # HARNESS_CONFIG is resolved by the caller before this step, not written into config values.
        raw_value = env[variable]
        if entry["kind"] == "SECRET_REFERENCE":
            value: Any = {"source": "env", "name": variable}
        elif raw_value.lower() in ("true", "false"):
            value = raw_value.lower() == "true"
        else:
            value = raw_value
        *path, leaf = entry["target_path"].split(".")
        cursor = result
        for segment in path:
            cursor = cursor.setdefault(segment, {})
        cursor[leaf] = value
        if path[:1] == ["providers"] and len(path) == 2:
            # A provider-scoped secret reference (e.g. HARNESS_PROVIDER_OPENAI_KEY
            # -> providers.openai.api_key) implicitly declares that provider's
            # adapter when the operator has not already declared it explicitly.
            cursor.setdefault("adapter", path[1])
    return result


# ---------------------------------------------------------------------------
# Full resolution pipeline + ConfigDigest (9.9.5)
# ---------------------------------------------------------------------------


def resolve_configuration(
    *,
    system_document: dict[str, Any] | None,
    user_document: dict[str, Any] | None,
    repository_document: dict[str, Any] | None,
    explicit_document: dict[str, Any] | None,
    env: dict[str, str],
    cli_overrides: dict[str, Any] | None = None,
    contracts_root: Path | None = None,
) -> dict[str, Any]:
    """Full ConfigurationSchema v1 pipeline: alias-migrate each present
    source, merge in ordinary precedence with security monotonicity applied
    to each security-bearing layer, apply registered environment overrides and CLI
    overrides, then strictly validate the result against
    `EffectiveConfiguration`.
    """
    registry = load_registry(contracts_root)
    aliases = registry["aliases"]
    canonical_keys = registry["canonical_top_level_keys"]
    defaults = registry["required_defaults"]

    raw_sources = [
        (name, document)
        for name, document in (
            ("system_config", system_document),
            ("user_config", user_document),
            ("repository_config", repository_document),
            ("explicit_config_file", explicit_document),
        )
        if document is not None
    ]
    check_cross_source_alias_conflict(raw_sources, aliases)

    layers: list[tuple[str, dict[str, Any]]] = [("built_in_defaults", defaults)]

    # Security is an intersection across every supplied configuration layer,
    # not an ordinary last-writer-wins merge.  Defaults are fallbacks rather
    # than an authority constraint: the first explicit layer may configure a
    # value, but every later layer can only narrow the accumulated scope.
    effective_security: dict[str, Any] = {}
    for name, document in (
        ("system_config", system_document),
        ("user_config", user_document),
        ("repository_config", repository_document),
        ("explicit_config_file", explicit_document),
    ):
        if document is None:
            continue
        migrated = migrate_aliases(document, aliases)
        validate_top_level_keys(migrated, canonical_keys)
        security_layer = migrated
        if effective_security:
            security_layer = apply_security_monotonicity(effective_security, migrated)
        layers.append((name, security_layer))
        effective_security = _deep_merge(effective_security, security_layer)

    merged = merge_layers(layers)
    env_layer = apply_env_overrides({}, env, registry["env_overrides"])
    if env_layer:
        env_layer = apply_security_monotonicity(effective_security, env_layer) if effective_security else env_layer
        merged = _deep_merge(merged, env_layer)
    if cli_overrides:
        cli_layer = apply_security_monotonicity(effective_security, cli_overrides) if effective_security else cli_overrides
        merged = _deep_merge(merged, cli_layer)

    validator = _effective_configuration_validator(contracts_root)
    errors = sorted(validator.iter_errors(merged), key=str)
    if errors:
        reason = REASON_CODE_CONFIG_UNKNOWN_KEY if any("Additional properties" in e.message for e in errors) else REASON_CODE_CONFIG_INVALID
        raise ConfigError(f"resolved configuration failed EffectiveConfiguration validation: {[e.message for e in errors]}", reason_code=reason)

    return merged


def compute_config_digest(effective_configuration: dict[str, Any]) -> str:
    """9.9.5: ConfigDigest over effective non-secret configuration plus stable
    secret-reference metadata. Secret plaintext never appears in canonical
    configuration values (only `SecretRef {source, name}` objects do), so no
    separate exclusion step is required beyond canonicalizing the resolved
    object as-is.
    """
    _reject_plaintext_secret_configuration(effective_configuration)
    try:
        return digest_for(effective_configuration)
    except CanonicalizationError as exc:
        raise ConfigError(str(exc), reason_code=exc.reason_code) from exc


def _reject_plaintext_secret_configuration(configuration: dict[str, Any]) -> None:
    """Keep ConfigDigest input inside the SecretRef-only configuration domain."""
    providers = configuration.get("providers", {})
    if isinstance(providers, dict):
        for provider_name, provider in providers.items():
            if not isinstance(provider, dict) or "api_key" not in provider:
                continue
            value = provider["api_key"]
            if value is not None and not _is_secret_ref(value):
                raise ConfigError(
                    f"providers.{provider_name}.api_key must be a secret reference, never plaintext",
                    reason_code=REASON_CODE_CONFIG_INVALID,
                )
    secrets = configuration.get("secrets", {})
    if isinstance(secrets, dict):
        for secret_name, value in secrets.items():
            if not _is_secret_ref(value):
                raise ConfigError(
                    f"secrets.{secret_name} must be a secret reference, never plaintext",
                    reason_code=REASON_CODE_CONFIG_INVALID,
                )


def _is_secret_ref(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"source", "name"}
        and value.get("source") == "env"
        and isinstance(value.get("name"), str)
        and bool(value["name"])
    )
